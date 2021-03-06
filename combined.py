import pandas
import numpy
import general
import discretionary_aua
import vantage_aua

idx = pandas.IndexSlice
nnc_nnb_multiple_factor = 0.035
nnc_nnb_intercept_factor = 631.8

# ==== 95% Confidence interval ====
nnc_nnb_multiple_ci_upper = 0.0447
nnc_nnb_multiple_ci_lower = 0.0252
nnc_nnb_intercept_ci_upper = 929.833
nnc_nnb_intercept_ci_lower =333.7678

def historic_aua(dic_data):
    dis = discretionary_aua.compute_historic_aua(dic_data)
    van = vantage_aua.compute_historic_aua(dic_data)
    aua = pandas.concat([dis,van], axis='columns')
    return aua

def historic_nnb_distribution(dic_data, input_dic):
    total = total_historic_nnb(dic_data, input_dic)
    result = (general.monthly_fulfill(input_dic)['nnb distribution']).reindex(index=general.month_end_series).multiply(total['NNB'], axis='index')
    result.iloc[0,:] = 0
    return result

def compounded_historic_nnb_distribution_effect(dic_data, input_dic):
    df = total_nnb_distribution_clientAlgo(dic_data, input_dic)
    df[df.index > pandas.to_datetime(general.last_day_prev_month)] = 0
    disc_comp = discretionary_aua.get_composite_return(dic_data)
    df.loc[:,general.disc_known_cols] = df.loc[:,general.disc_known_cols].multiply(disc_comp,axis='index')
    ftse_all_shares = dic_data['Index price'].loc[:,['FTSE All Share','FTSE All Share TR']].reindex(index=general.month_end_series)
    returns = (ftse_all_shares / ftse_all_shares.shift(1).fillna(method='bfill') - 1).mean(axis='columns')
    df.loc[:,'vantage_other_shares_aua'] = df.loc[:,'vantage_other_shares_aua'] * returns
    vantage_comp = vantage_aua.other_funds_composite_return(dic_data)
    df.loc[:,'vantage_other_funds_aua'] = df.loc[:,'vantage_other_funds_aua'] * vantage_comp
    return df

    

def future_nnb_distribution(dic_data, input_dic):
    total = total_future_nnb(dic_data, input_dic)
    result = (general.monthly_fulfill(input_dic)['nnb distribution']).reindex(index=general.month_end_series).multiply(total['NNB'], axis='index')
    result.iloc[0,:] = 0
    return result

def total_historic_aua(dic_data, input_dic):
    aua = historic_aua(dic_data)
    #nnb = historic_nnb_distribution(dic_data, input_dic).cumsum(axis='index')
    nnb_effect = compounded_historic_nnb_distribution_effect(dic_data, input_dic).cumsum(axis='index')   # new nnb algo
    
    result = aua + nnb_effect.loc[:,aua.columns]
    return result


def future_aua(dic_data, input_dic):
    aua = total_historic_aua(dic_data, input_dic)
    compound_rate = general.fillna_monthly(input_dic['compound growth']).reindex(index=general.month_end_series).applymap(general.compound_growth_rate)
    compound_rate[compound_rate.index <= pandas.to_datetime(general.last_day_prev_month)] = 0
    sliced_compound_rate = compound_rate.loc[general.last_day_prev_month:,:]
    sliced_aua = aua.loc[general.last_day_prev_month:,:].fillna(method='ffill')
    working_compound = (sliced_compound_rate+1).cumprod()
    sliced_aua = sliced_aua.multiply(working_compound['compound growth rate'], axis='index')
    return sliced_aua.reindex(general.month_end_series)

def total_future_aua(dic_data, input_dic):
    aua = future_aua(dic_data, input_dic)
    nnb = future_nnb_distribution(dic_data, input_dic).cumsum(axis='index')    # new nnb algo
    
    result = aua + nnb.loc[:,aua.columns]
    return result

def get_total_asset_nnb(dic_data, input_dic):
    sliced_aua = future_aua(dic_data, input_dic)
    sliced_aua = sliced_aua.loc[general.last_day_prev_month:,:]
    
    future_total_asset_nnb = sliced_aua.loc[:,general.disc_known_cols].sum(axis='columns') + sliced_aua.loc[:,general.vantage_known_cols].sum(axis='columns')
    return future_total_asset_nnb

def get_historic_implied_nnb(dic_data,idx=general.month_end_series,funds_opt=None,total=True):
    '''
    Return a series of total historic implied nnb which is the sum of all the funds in HL
    dictionary of data
    '''
    if funds_opt=='no_select':
        mod_acc_price = dic_data['acc price'].drop(['Select UK Growth Shares', 'Select UK Income Shares', 'Select Global Growth Shares'], axis='columns')
        mod_inc_price = dic_data['inc price'].drop(['Select UK Growth Shares', 'Select UK Income Shares', 'Select Global Growth Shares'], axis='columns')
        mod_acc_size = dic_data['acc size'].drop(['Select UK Growth Shares', 'Select UK Income Shares', 'Select Global Growth Shares'], axis='columns')
        mod_inc_size = dic_data['inc size'].drop(['Select UK Growth Shares', 'Select UK Income Shares', 'Select Global Growth Shares'], axis='columns')
    else:
        mod_acc_price = dic_data['acc price']
        mod_inc_price = dic_data['inc price']
        mod_acc_size = dic_data['acc size']
        mod_inc_size = dic_data['inc size']
    
    acc_bid_price = mod_acc_price.reindex(index=idx).fillna(method='ffill')
    inc_bid_price = mod_inc_price.reindex(index=idx).fillna(method='ffill')
    acc_bid_return = acc_bid_price / acc_bid_price.shift(1) - 1
    inc_bid_return = inc_bid_price / inc_bid_price.shift(1) - 1
    
    acc_size = mod_acc_size.reindex(index=idx).fillna(method='ffill')
    inc_size = mod_inc_size.reindex(index=idx).fillna(method='ffill')
    acc_size_change = acc_size / acc_size.shift(1) - 1
    inc_size_change = inc_size / inc_size.shift(1) - 1
    
    acc_nnb = (acc_size_change - acc_bid_return) * acc_size.shift(1)
    inc_nnb = (inc_size_change - inc_bid_return) * inc_size.shift(1)
    
    if total:
        total_nnb = acc_nnb.sum(axis='columns') + inc_nnb.sum(axis='columns')
    else:
        total_nnb = acc_nnb.fillna(0) + inc_nnb.fillna(0)
    return total_nnb


def total_historic_nnb(dic_data, input_dic, idx=general.month_end_series):
    '''
    Function that returns a total historical nnb based on the implied nnb on months that we do not have the total nnb data
    dic_data: fund data
    input_dic: dictionary of inputs which include nnb distribution
    '''
    implied_discretionary_nnb = get_historic_implied_nnb(dic_data,idx=idx)  # series
    monthly_filled_inputs = general.monthly_fulfill(input_dic)
    
    total_historical_nnb = dic_data['total nnb'].reindex(index=idx)
    implied_total_nnb = (implied_discretionary_nnb / monthly_filled_inputs['nnb distribution'].reindex(index=idx)[general.disc_known_cols].sum(axis='columns')).to_frame(name='NNB') # dataframe
    '''
    Pandas version 0.21 fixed the following bug!
    result = implied_total_nnb[total_historical_nnb.isnull()].fillna(0.0) + total_historical_nnb.fillna(0.0)
    
    '''
    
    result = pandas.concat([total_historical_nnb[~numpy.isnan(total_historical_nnb.values)], implied_total_nnb[numpy.isnan(total_historical_nnb.values)]], axis='index')
    
    return result 
    

def total_future_nnb(dic_data, input_dic,idx=general.month_end_series):
    year_nnb_percent = (input_dic['nnb pcent total asset'].fillna(method='ffill').fillna(method='bfill'))['nnb pcent total asset'].to_dict()
    df = general.compute_quarter_half_no(idx)
    df = df.set_index('month_end')
    
    df.loc[:,'nnb pcent total asset'] = df['financial_year'].map(year_nnb_percent).values
    df.loc[:,'nnb quarterly distribution'] = (df['quarter_no'].map(general.nnb_quarterly_dist).values)/3
    df['nnb pcent'] = df['nnb pcent total asset'] * df['nnb quarterly distribution']
    df.loc[general.last_day_prev_month,'nnb pcent'] = 0.0
    nnb_pcent_working = df.loc[general.last_day_prev_month:,:]['nnb pcent']
    df2 = get_total_asset_nnb(dic_data, input_dic)
    result = (df2 * nnb_pcent_working).to_frame(name='NNB').reindex(index=idx).fillna(0.0)
    return result



def total_nnb(dic_data, input_dic, idx=general.month_end_series, opt=None):
    df = total_historic_nnb(dic_data, input_dic, idx) + total_future_nnb(dic_data, input_dic, idx)
    if opt is None:
        return df
    else:
        if opt == 'financial_year' or opt == 'calendar_year':
            return general.convert_fy_quarter_half_index(df, df.index).groupby(opt).sum(min_count=1)
        elif opt == 'month_no':
            return general.convert_fy_quarter_half_index(df, df.index).groupby(['calendar_year',opt]).sum(min_count=1)
        else:
            return general.convert_fy_quarter_half_index(df, df.index).groupby(['financial_year',opt]).sum(min_count=1)
        
def nnb_distribution(dic_data, input_dic,idx=general.month_end_series, opt=None):
    total = total_nnb(dic_data,input_dic,idx, opt)
    result = (general.monthly_fulfill(input_dic)['nnb distribution']).reindex(index=idx).multiply(total['NNB'], axis='index')
    result.iloc[0,:] = 0
    if opt is None:
        return result
    else:
        if opt == 'financial_year' or opt == 'calendar_year':
            return general.convert_fy_quarter_half_index(result, result.index).groupby(opt).sum(min_count=1)
        elif opt == 'month_no':
            return general.convert_fy_quarter_half_index(result, result.index).groupby(['calendar_year',opt]).sum(min_count=1)
        else:
            return general.convert_fy_quarter_half_index(result, result.index).groupby(['financial_year',opt]).sum(min_count=1)

def total_client_predt(dic_data, input_dic):
    clients = general.convert_fy_quarter_half_index(dic_data['clients'],dic_data['clients'].index)
    clients = clients.groupby(['financial_year','quarter_no']).sum(min_count=1)
    predt_clients = clients['No. of clients'].copy()
    
    nnc_pcent = input_dic['nnc pcent total client']
    nnc_pcent = general.convert_fy_quarter_half_index(nnc_pcent,nnc_pcent.index).groupby(['financial_year','quarter_no']).sum(min_count=1)
    
    for i in range(1,predt_clients.size):
        if ~numpy.isnan(predt_clients.iloc[i-1]) & numpy.isnan(predt_clients.iloc[i]):
            predt_clients.iloc[i] = round((predt_clients.iloc[i-1] * (1+nnc_pcent['nnc pcent total client'].iloc[i]))-0.5,0)
    return predt_clients

def net_new_client_predt(dic_data, input_dic):
    p_cs = total_client_predt(dic_data, input_dic)
    net_new_clients = p_cs - p_cs.shift(1)
    return net_new_clients

def total_nnb_ci_clientAlgo(dic_data, input_dic, opt=None):
    nnb = general.convert_fy_quarter_half_index(dic_data['total nnb'],dic_data['total nnb'].index)
    nnb = nnb.groupby(['financial_year','quarter_no']).sum(min_count=1)
    net_new_clients = net_new_client_predt(dic_data, input_dic)
    
    nnb['Lower bound'] = nnb['NNB'].values
    nnb['Upper bound'] = nnb['NNB'].values
    
    for j in range(1,nnb.index.size):
        if numpy.isnan(nnb.iloc[j,0]) & ~numpy.isnan(nnb.iloc[j-1,0]):
            nnb.iloc[j,0] = (net_new_clients.iloc[j] * nnc_nnb_multiple_factor + nnc_nnb_intercept_factor) * 1000000
    for j in range(1,nnb.index.size):
        if numpy.isnan(nnb.iloc[j,1]) & ~numpy.isnan(nnb.iloc[j-1,1]):
            nnb.iloc[j,1] = (net_new_clients.iloc[j] * nnc_nnb_multiple_ci_lower + nnc_nnb_intercept_ci_lower) * 1000000
    
    for j in range(1,nnb.index.size):
        if numpy.isnan(nnb.iloc[j,2]) & ~numpy.isnan(nnb.iloc[j-1,2]):
            nnb.iloc[j,2] = (net_new_clients.iloc[j] * nnc_nnb_multiple_ci_upper + nnc_nnb_intercept_ci_upper) * 1000000
    
    df = convert_quarter_to_month_nnb(nnb, opt='Confidence interval')
    if opt is None:
        return df
    else:
        if opt == 'financial_year' or opt == 'calendar_year':
            return general.convert_fy_quarter_half_index(df, df.index).groupby(opt).sum(min_count=1)
        elif opt == 'month_no':
            return general.convert_fy_quarter_half_index(df, df.index).groupby(['calendar_year',opt]).sum(min_count=1)
        else:
            return general.convert_fy_quarter_half_index(df, df.index).groupby(['financial_year',opt]).sum(min_count=1)

def convert_quarter_to_month_nnb(nnb_c, opt=None):
    month_nnb_dist = pandas.DataFrame(columns=['% dist'], index=general.month_end_series)
    month_nnb_c = general.convert_fy_quarter_half_index(month_nnb_dist,month_nnb_dist.index).reset_index()
    dist_nnb = {33:0.5,44:0.5,32:0.25,31:0.25,45:0.25,46:0.25,17:1.0/3,18:1.0/3,19:1.0/3,210:1.0/3,211:1.0/3,212:1.0/3 }
    month_nnb_dist['% dist'] = month_nnb_c['quarter_no'].replace(dist_nnb).values
    month_nnb_c['temp'] = (month_nnb_c['quarter_no'].map(str) + month_nnb_c['month_no'].map(str)).map(int)
    month_nnb_dist['% dist'] = month_nnb_c['temp'].replace(dist_nnb).values
    month_nnb_c['temp2'] = (month_nnb_c['financial_year'].map(str) + month_nnb_c['quarter_no'].map(str)).map(int)
    nnb_working = nnb_c.reset_index()
    nnb_working['temp'] = (nnb_working['financial_year'].map(str) + nnb_working['quarter_no'].map(str)).map(int)
    if opt is None:
        nnb_working = (nnb_working.set_index('temp').drop(['financial_year','quarter_no'],axis='columns')).to_dict()['NNB']
        month_nnb_dist['nnb'] = month_nnb_c['temp2'].replace(nnb_working).values
        month_nnb_dist['NNB'] = month_nnb_dist['nnb'] * month_nnb_dist['% dist']
        
        df = month_nnb_dist.drop(['% dist', 'nnb'], axis='columns')
    elif opt == 'Confidence interval':
        nnb_w = (nnb_working.set_index('temp').drop(['financial_year','quarter_no'],axis='columns')).to_dict()['NNB']
        nnb_lower = (nnb_working.set_index('temp').drop(['financial_year','quarter_no'],axis='columns')).to_dict()['Lower bound']
        nnb_upper = (nnb_working.set_index('temp').drop(['financial_year','quarter_no'],axis='columns')).to_dict()['Upper bound']
        month_nnb_dist['nnb'] = month_nnb_c['temp2'].replace(nnb_w).values
        month_nnb_dist['nnb_lower'] = month_nnb_c['temp2'].replace(nnb_lower).values
        month_nnb_dist['nnb_upper'] = month_nnb_c['temp2'].replace(nnb_upper).values
        month_nnb_dist['NNB'] = month_nnb_dist['nnb'] * month_nnb_dist['% dist']
        month_nnb_dist['Lower bound'] = month_nnb_dist['nnb_lower'] * month_nnb_dist['% dist']
        month_nnb_dist['Upper bound'] = month_nnb_dist['nnb_upper'] * month_nnb_dist['% dist']
        
        df = month_nnb_dist.drop(['% dist', 'nnb', 'nnb_lower', 'nnb_upper'], axis='columns')
    
    return df
    
    
    
    
def total_nnb_clientAlgo(dic_data, input_dic, opt=None):
    nnb = general.convert_fy_quarter_half_index(dic_data['total nnb'],dic_data['total nnb'].index)
    nnb = nnb.groupby(['financial_year','quarter_no']).sum(min_count=1)
    net_new_clients = net_new_client_predt(dic_data, input_dic)
    
    nnb_c = nnb['NNB'].copy()
    for j in range(1,nnb_c.size):
        if numpy.isnan(nnb_c.iloc[j]) & ~numpy.isnan(nnb_c.iloc[j-1]):
            nnb_c.iloc[j] = (net_new_clients.iloc[j] * nnc_nnb_multiple_factor + nnc_nnb_intercept_factor) * 1000000
    
    # converting quarter nnb to monthly
    df = convert_quarter_to_month_nnb(nnb_c)
    if opt is None:
        return df
    else:
        if opt == 'financial_year' or opt == 'calendar_year':
            return general.convert_fy_quarter_half_index(df, df.index).groupby(opt).sum(min_count=1)
        elif opt == 'month_no':
            return general.convert_fy_quarter_half_index(df, df.index).groupby(['calendar_year',opt]).sum(min_count=1)
        else:
            return general.convert_fy_quarter_half_index(df, df.index).groupby(['financial_year',opt]).sum(min_count=1)

def total_nnb_distribution_clientAlgo(dic_data, input_dic, opt=None):
    total = total_nnb_clientAlgo(dic_data, input_dic)
    result = (general.monthly_fulfill(input_dic)['nnb distribution']).reindex(index=general.month_end_series).multiply(total['NNB'], axis='index')
    result.iloc[0,:] = 0
    if opt is None:
        return result
    else:
        if opt == 'financial_year' or opt == 'calendar_year':
            return general.convert_fy_quarter_half_index(result, result.index).groupby(opt).sum(min_count=1)
        elif opt == 'month_no':
            return general.convert_fy_quarter_half_index(result, result.index).groupby(['calendar_year',opt]).sum(min_count=1)
        else:
            return general.convert_fy_quarter_half_index(result, result.index).groupby(['financial_year',opt]).sum(min_count=1)

def total_aua(dic_data, input_dic):
    # ====== old hlf algo=======================
    # future = total_future_aua(dic_data, input_dic)
    # future.loc[general.last_day_prev_month,:] = 0.0
    # past = total_historic_aua(dic_data, input_dic)
    # final_aua = future.fillna(0.0) + past.fillna(0.0)
    
    # ======== new net new client algo ===============
    future = future_aua(dic_data, input_dic)
    future.loc[general.last_day_prev_month,:] = 0.0
    past = historic_aua(dic_data)
    final_aua = future.fillna(0.0) + past.fillna(0.0) + total_nnb_distribution_clientAlgo(dic_data, input_dic).cumsum()
    
    final_aua.loc[:,'hlf_aua'] = final_aua.loc[:,'vantage_hlf_aua'] + final_aua.loc[:,'thirdparty_hlf_aua'] + final_aua.loc[:,'pms_hlf_aua']
    final_aua.loc[:,'pms_aua'] = final_aua.loc[:,'pms_others_aua'] + final_aua.loc[:,'pms_hlf_aua']
    final_aua.loc[:,'discretionary_aua'] = final_aua.loc[:,'vantage_hlf_aua'] + final_aua.loc[:,'thirdparty_hlf_aua'] + final_aua.loc[:,'pms_aua']
    final_aua.loc[:,'vantage_shares_aua'] = final_aua.loc[:,'vantage_hl_shares_aua'] + final_aua.loc[:,'vantage_other_shares_aua']
    final_aua.loc[:,'vantage_aua'] = final_aua.loc[:,'vantage_shares_aua'] + final_aua.loc[:,'vantage_other_funds_aua'] + final_aua.loc[:,'vantage_hlf_aua'] + final_aua.loc[:,'vantage_cash_aua']
    final_aua.loc[:,'total_hlf_aua'] = final_aua.loc[:,'hlf_aua']
    final_aua.loc[:,'total_funds_aua'] = final_aua.loc[:,'vantage_hlf_aua'] + final_aua.loc[:,'vantage_other_funds_aua'] + final_aua.loc[:,'pms_hlf_aua']
    
    
    def cash_aua_temp(df, y2=98000000):
        test = df['cash_service_aua'].copy()
        
        test[(test.index>'2019-06-28')] = y2 
        
        test[(test.index>'2020-06-28')] = 160000000
        test[(test.index>'2021-06-30')] = 320000000
        test[(test.index>'2022-06-30')] = 480000000
        return test.cumsum()
    
    cash_temp = cash_aua_temp(final_aua)
    
    final_aua.loc[:,'cash_service_aua'] = cash_temp
    
    
    final_aua.loc[:,'total_assets_aua'] = final_aua.loc[:,'vantage_aua'] + final_aua.loc[:,'pms_aua'] + final_aua.loc[:,'cash_service_aua']
    
    final_aua.loc[:,'Funds'] = final_aua.loc[:,'total_funds_aua']
    final_aua.loc[:,'Shares'] = final_aua.loc[:,'vantage_shares_aua']
    final_aua.loc[:,'HLF'] = final_aua.loc[:,'total_hlf_aua']
    final_aua.loc[:,'Cash'] = final_aua.loc[:,'vantage_cash_aua'] + final_aua.loc[:,'pms_others_aua']
    final_aua.loc[:, 'SIPP'] = final_aua.loc[:, 'vantage_aua'] * general.account_aua_dist['sipp']
    final_aua.loc[:, 'ISA'] = final_aua.loc[:, 'vantage_aua'] * general.account_aua_dist['isa']
    final_aua.loc[:, 'F&S'] = final_aua.loc[:, 'vantage_aua'] * general.account_aua_dist['f&s']
    
    
    
    result = general.convert_fy_quarter_half_index(final_aua, general.month_end_series)
    
    
    
    return result
    
def accounts_dist_predt(data_dic, input_dic):
    account_data = data_dic['no_of_accounts']
    total_predicted_clients = total_client_predt(data_dic, input_dic).to_frame()
    semi_annual_total_clients = total_predicted_clients.loc[idx[:, [2, 4]], :]
    total_client_change = semi_annual_total_clients / semi_annual_total_clients.shift(1) - 1
    reindexed_account_data = general.convert_fy_quarter_half_index(account_data, account_data.index).reset_index()
    current_account_dist = reindexed_account_data.drop(['half_no', 'calendar_year', 'month_no', 'month_end'], axis='columns').set_index(['financial_year', 'quarter_no'])
    current_account_dist.columns = ['sipp', 'isa', 'f&s']
    current_total_accounts_df = current_account_dist.sum(axis='columns').to_frame()
    current_total_accounts_df.columns = ['total_clients']
    current_total_accounts_df = current_total_accounts_df.where(current_total_accounts_df != 0)
    temp_total_accounts_df = current_total_accounts_df.fillna(method='ffill').where(current_total_accounts_df.isna())
    temp_total_accounts_df = temp_total_accounts_df.reindex(total_client_change.index).fillna(method='ffill')
    multipliers = (total_client_change.where(temp_total_accounts_df['total_clients'].notna()) + 1).cumprod()
    total_predicted_accounts = temp_total_accounts_df['total_clients'] * multipliers['No. of clients']

    account_dist_df = pandas.DataFrame(index=total_predicted_accounts.index, columns=['sipp', 'isa', 'f&s'])
    for account_type in general.account_dist:
        account_dist_df[account_type] = general.account_dist[account_type] * total_predicted_accounts
    from numpy import nan
    final_account_dist_df = (account_dist_df.fillna(0) + current_account_dist.reindex(index=account_dist_df.index).fillna(0)).replace(0, nan)
    return final_account_dist_df



    
    