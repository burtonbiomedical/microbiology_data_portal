#Import Dependencies
import pymongo
import sys
import os
import pandas as pd
import re
import pickle
import matplotlib.pyplot as plt
import numbers
import numpy as np
import seaborn as sns
from datetime import datetime, date
import errno
import json
from itertools import chain
from collections import defaultdict
import math

class ExtractData:
    def __init__(self, db_name, mongo_client):
        """Inintialise database connection
        args:-
        db_name: Name of the database to search (must be of expected format)]
        mongo_client: pymongo client object"""
        
        self.db = mongo_client[db_name]
        self.all_orgs = self.db.organism_index
        
    def get_mic_data(self, organism):
        """Returns a list of dictionary objects, containing MIC data for all isolates for
        specified bacterial species.
        Return list of 
        args:-
        organism: The organism to search for. Regular expressions are accepted"""
        report_ids = self.get_reportIDs(organism)
        total_mic_data = list(map(self.extract_report_mic_data, report_ids))
        intended_organism_data = self.remove_irrelevant_isolates(organism, total_mic_data)
        return intended_organism_data
        
    def get_reportIDs(self, organism):
        """Get report IDs for organism of interest
        Returns list of report IDs
        args:-
        organism: the bacterial organism of interest (accepts regular expressions)"""
        
        report_summaries = list(self.all_orgs.find({'organism_name': {'$regex':organism}}))
        report_ids = []
        for x in report_summaries:
            report_ids += x['reports']
        return report_ids
        
    def extract_report_mic_data(self, reportID):
        """Get MIC data for a single report
        Returns MIC data for all isolates in a report, as list of dictionaries.
        args:-
        reportID: the report ID for the report to search for"""
        
        report = list(self.db.reports.find({'_id':reportID}))[0]
        mic_data = report['organism_summary']
        return mic_data
    
    def remove_irrelevant_isolates(self, intended_organism, total_mic_data):
        """Report MIC array may contain data for desired organism, but accompanied with data for irrelvant
        organisms i.e. a report with multiple isolates. This function removes all isolates that are not of interest
        Returns a single array of dictionaries containing only those with organism of interest.
        args:-
        intended_organism: the organism that we are collecting data for
        extracted_mic_data: the total MIC summaries for all isolates from all reports as an array of dictionaries"""
        intended_organism_data = []
        for l in total_mic_data:
            for org in l:
                org_name = org['isolate_data']['organism_name']
                if re.compile(intended_organism, re.IGNORECASE).search(org_name):
                    intended_organism_data.append(org)
        return intended_organism_data

    def to_pickle(self, mic_data, path, filename):
        """Export data as serialised python object
        args:-
        mic_data: extracted mic data as list of python dictionaries
        filename: file to save data too, with file extension 'pickle'"""
        with open("{}{}".format(path, filename), 'wb') as file:
            pickle.dump(mic_data, file)

class ProcessData():
    """Class for creating pandas dataframe and data exploration. Class expects a single organism MIC data file,
    as serialised python dictionary."""
    def __init__(self, organism_mic_data_path, start_date=None, end_date=None):
        """args:-
        organism_mic_data_filename: string - organism mic data pickle file path"""
        self.mic_data = pickle.load(open(organism_mic_data_path, 'rb'))
        self.mic_dataframe = self.build_dataframe(start_date, end_date)
        
    def build_dataframe(self, start_date, end_date):
        """Creates pandas dataframe using mic data from pickle file
        Returns dataframe object
        args:-
        Specify date range using start and end dates:
        start_date: string of format YYYY-MM-DD or datetime object
        end_date: string of format YYYY-MM-DD or datetime object"""
    
        def get_drug_mic_data(drugMIC):
            """Creates dictionary object of format drugname:result from mic data dictionary values"""
            drugName = drugMIC['drug']
            #Antibiotic result can be of type MIC value, or an interpretation e.g. + or -
            if 'mic' in list(drugMIC.keys()):
                drugResult = drugMIC['mic']
            else:
                drugResult = drugMIC['interpretation']
            return {drugName: drugResult}
        
        def build_row_object(isolate):
            """Builds dictionary object representing a single row, that details a single isolate"""
            mic_data = isolate['isolate_data']['mic_data']    
            drug_mic_data = list(map(lambda x: get_drug_mic_data(x), mic_data))
            row = {drug:result for drugResult in drug_mic_data for drug,result in drugResult.items()}
            row['isolate_date'] = isolate['isolate_date']
            row['species'] = isolate['isolate_data']['organism_name']
            return row
        
        def convert_interpretations(val):
            """Some antimicrobial columns actually correspond to screening tests that have
            a positive or negative interpretation. This function changes these interpretations to 1 
            or 0 respectively"""
            try:
                if val == '-':
                    return 0.0
                elif val == '+':
                    return 1.0
                else:
                    return float(val)
            except:
                return val    
        
        df_rows = []
        for isolate in self.mic_data:
            if start_date != None and end_date != None:
                start_date = datetime.strptime(str(start_date), '%Y-%m-%d').date()
                end_date = datetime.strptime(str(end_date), '%Y-%m-%d').date()
                isolate_date = datetime.date(isolate['isolate_date'])
                if (isolate_date >= start_date) and (isolate_date <= end_date):
                    df_rows.append(build_row_object(isolate))
            else:
                df_rows.append(build_row_object(isolate))
        df = pd.DataFrame.from_dict(df_rows)
        df.sort_values('isolate_date', inplace=True)
        df.set_index('isolate_date', inplace=True, drop=True)
        df = df.apply(lambda x: x.apply(lambda y: None if y == 'UNKNOWN' else y), axis=1)
        df.dropna(how='all', inplace=True, axis=1)
        df = df.apply(lambda x: x.apply(convert_interpretations), axis=0)

        return df
        
    def get_dataframe(self):
        """Return pandas dataframe object"""
        return self.mic_dataframe.copy(deep=True)
    
    def to_excel(self, path):
        """Save pandas dataframe object as excel file
        args:- 
        path: string - path to save file too"""
        writer = pd.ExcelWriter(path, engine='xlsxwriter')
        self.mic_dataframe.to_excel(writer)
        writer.save()
        return path
    
    def antibiotic_series(self, antibiotic, remove_outliers=False):
        """Generate a pandas series object for specified antibiotic.
        args:-
        antibiotic: string - antibiotic of interest
        remove_outliers: integer - standard deviations either side of the mean to remain included in series data. 
        Default = False, will include all data."""
        antibiotic_data = self.mic_dataframe[antibiotic].copy()
        antibiotic_data = pd.to_numeric(antibiotic_data, errors='coerce')
        antibiotic_data.dropna(inplace=True)
        if remove_outliers != False:
            antibiotic_data = antibiotic_data[np.abs(antibiotic_data-antibiotic_data.mean())
                               <=(remove_outliers*antibiotic_data.std())]
        return antibiotic_data
    
    def antibiotic_descriptives(self, antibiotic, remove_outliers=False, save_path="/", error_path='/'):
        """Return descriptive statistics for requested antibiotic
        args:-
        antibiotic: string - antibiotic of interest
        remove_outliers: integer - standard deviations either side of the mean to remain included in series data. 
        Default = False, will include all data."""
        try:
            antibiotic_data = self.antibiotic_series(antibiotic, remove_outliers=remove_outliers)
            stats = {'Oldest_data_point': str(antibiotic_data.index.values[0])[0:10],
                'Newest_data_point': str(antibiotic_data.index.values[antibiotic_data.shape[0]-1])[0:10],
                    'Total_antibiotic_data_points': antibiotic_data.shape[0],
                    'Total_Isolates': self.mic_dataframe.shape[0],
                'Mean': round(antibiotic_data.mean(),3),
                    'SD': round(antibiotic_data.std(),3),
                    'Min': round(antibiotic_data.min(),3),
                    'Max': round(antibiotic_data.max(),3),
                    'Median': round(antibiotic_data.median(),3),
                'Sample_variance': round(antibiotic_data.var(),3),
                'Skewness': round(antibiotic_data.skew(),3),
                'Kurtosis': round(antibiotic_data.kurt(),3)}
        except:
            stats = {'error': 'error - unable to generate statistic'}
            return error_path
        
        json_obj = json.dumps(stats)
        with open(save_path, 'wb') as file:
          file.write(json_obj)
        return save_path
    
    def antibiotic_distribution_curve(self, antibiotic, bins='auto', remove_outliers=False, save_path='/', error_path='/'):
        """Generate distribution curve for selected antibiotic.
        args:-
        antibiotic: string - antibiotic of interest
        bins: integer/string - see numpy.histogram documentation for bins
        remove_outliers: integer - standard deviations either side of the mean to remain included in series data. 
        Default = False, will include all data."""
        try:
            antibiotic_data = self.antibiotic_series(antibiotic, remove_outliers=remove_outliers).values
            hist, bins = np.histogram(antibiotic_data, bins=bins)
            fig,ax = plt.subplots(figsize=(10,5))
            ax.plot(bins[:-1], hist)
            plt.title('Distribution of MIC values for {}'.format(antibiotic))
            with open(save_path, 'wb') as file:
                plt.savefig(file)
            return save_path
        except:
            return error_path

        
    def antibiotic_timeseries(self, antibiotic, intervals='M', remove_outliers=False):
        """Generate timeseries with mean MIC value and standard deviations, using the time interval provided.
        args:-
        antibiotic: string - antibiotic of interest
        interval: integer/string - see pandas documentation
        remove_outliers: integer - standard deviations either side of the mean to remain included in series data. 
        Default = False, will include all data."""
        antibiotic_data = self.antibiotic_series(antibiotic, remove_outliers=remove_outliers)
        means = antibiotic_data.resample(intervals).mean().rename('Mean MIC')
        std = antibiotic_data.resample(intervals).std().rename('SD')
        totals = antibiotic_data.resample(intervals).count().rename('Total isolates')
        return pd.concat([means,std, totals], axis=1).round(3)
    
    def antibiotic_trend_analysis(self, antibiotic, intervals='3M', 
                                  include_sd=True, remove_outliers=False, save_path='/', error_path='/'):
        """Generate trend line plot for mean MIC value over time, with line of best fit generated using 
        first degree polynomial regression.
        args:-
        antibiotic: string - antibiotic of interest
        interval: integer/string - see pandas documentation
        include_sd: boolean - include +/- 1 standard deviation either side of mean
        remove_outliers: integer - standard deviations either side of the mean to remain included in series data. 
        Default = False, will include all data."""
        try:
            fig,ax = plt.subplots(figsize=(10,5))
            timeseries = self.antibiotic_timeseries(antibiotic, intervals, remove_outliers=remove_outliers)
            timeseries.dropna(inplace=True)
            coefficients, residuals, _, _, _ = np.polyfit(range(len(timeseries.index)),timeseries['Mean MIC'],1,full=True)
            mse = residuals[0]/(len(timeseries.index))
            nrmse = np.sqrt(mse)/(timeseries['Mean MIC'].max() - timeseries['Mean MIC'].min()+1)
            regression_analysis = 'First degree polynomial regression -- Slope: {0:2.6}, Fitting error: {1:2.6}%'.format(
                np.round(coefficients[0], decimals=4), np.round(nrmse*100, decimals=6))
            ax.plot(timeseries.index.values, timeseries['Mean MIC'], label="Mean MIC")
            ax.plot(timeseries.index.values, [coefficients[0]*x + coefficients[1] for x in range(len(timeseries))])
            
            if include_sd:
                timeseries['SD +1'] = timeseries['Mean MIC'] + timeseries['SD']
                timeseries['SD -1'] = timeseries['Mean MIC'] - timeseries['SD']
                ax.plot(timeseries.index.values, timeseries['SD +1'], label="+1 SD")
                ax.plot(timeseries.index.values, timeseries['SD -1'], label="-1 SD")
                
            ax.legend(loc='upper right', shadow=True, fontsize='small')
            plt.suptitle('{} Mean Inhibitory Concentration vs Time'.format(antibiotic), fontsize=16)
            plt.title(regression_analysis, fontsize=12)
            plt.xlabel('Time')
            plt.ylabel('MIC')
            with open(save_path, 'wb') as file:
                plt.savefig(file)
            return save_path
        except:
            return error_path

        
    def correlation_matrix(self, antibiotics='all', null_threshold=0.5, save_path='/', error_path='/'):
        """Generate correlation matrix of all drug MIC values, and show as heatmap
        args:-
        antibiotics: list of strings - antibiotics to include in matrix
        null_threshold: float - the maximum percentage, taken as a percentage of dataset size, of null values
        a column can have without being excluded from correlation matrix"""
        try:
            if antibiotics == 'all':
                columns = self.mic_dataframe.columns.tolist()
            else:
                columns = antibiotics
                
            antibiotic_data = self.mic_dataframe[columns].copy()
            antibiotic_data = antibiotic_data.apply(lambda x: pd.to_numeric(x, errors='coerce'), axis=1)
            antibiotic_data = antibiotic_data.loc[:, (antibiotic_data.isnull().sum(axis=0)/
                                                    antibiotic_data.shape[0] < null_threshold)]
            corr_matrix = antibiotic_data.corr()
            plt.figure(figsize=(18,15))
            sns.set(font_scale=1.5)
            cmap = sns.cubehelix_palette(8, start=.5, rot=-.75, as_cmap=True)
            sns.heatmap(corr_matrix, annot=False, cmap=cmap)
            plt.yticks(rotation=0)
            plt.xticks(rotation=90)
            plt.title('Correlation matrix of MIC values')
            with open(save_path,'wb') as file:
                plt.savefig(file, pad_inches=1)
            return save_path
        except:
            return error_path
    
    def total_isolates_over_time(self, antibiotic, intervals='3M', save_path='/', error_path='/'):
        try:
            fig,ax = plt.subplots(figsize=(10,5))
            timeseries = self.antibiotic_timeseries(antibiotic, intervals)
            timeseries.dropna(inplace=True)
            ax.plot(timeseries.index.values, timeseries['Total isolates'])
            plt.title("Total Isolates Tested", fontsize=16)
            plt.xlabel('Time')
            plt.ylabel('# of Isolates')
            with open(save_path, 'wb') as file:
                plt.savefig(file)
            return save_path
        except:
            return error_path

def create_figures(myargs, save_path, pickle_file, start_date, end_date):
    drug = myargs['antibiotic']
    processing_data = ProcessData(pickle_file, start_date=start_date, end_date=end_date)
    
    if 'antibiotic' in myargs.keys():
        data_locations = {
            'descriptive_stats': "{}{}/descriptive_stats.json".format(save_path, drug),
            'distribution_curve_raw': "{}{}/figures/distribution.png".format(save_path,drug),
            'distribution_curve_without_outliers': "{}{}/figures/distribution_without_outliers.png".format(save_path,drug),
            'Mean_MIC_trend_without_sd': "{}{}/figures/MIC_Trend_without_SD.png".format(save_path,drug),
            'Mean_MIC_trend_without_sd_remove_outliers': "{}{}/figures/MIC_Trend_without_SD_remove_outliers.png".format(save_path,drug),
            'Mean_MIC_trend_with_sd_remove_outliers': "{}{}/figures/MIC_Trend_with_SD_remove_outliers.png".format(save_path,drug),
            'timeseries': "{}timeseries.json".format(save_path),
            'total_isolates': "{}{}/figures/total_isolates.png".format(save_path,drug),
            'Mean_MIC_trend_with_sd': "{}{}/figures/MIC_Trend_with_SD.png".format(save_path,drug),
            'error_path': "/home/rossco/Documents/web_projects/microbiology_data_portal/public/img/broken_robot.png"
            }
        
        data_locations['descriptive_stats'] = processing_data.antibiotic_descriptives(antibiotic=drug, save_path=data_locations['descriptive_stats'], error_path=data_locations['error_path'])

        data_locations['distribution_curve_raw'] = processing_data.antibiotic_distribution_curve(antibiotic=drug,bins=15, save_path=data_locations['distribution_curve_raw'],error_path=data_locations['error_path'])
        data_locations['distribution_curve_without_outliers'] = processing_data.antibiotic_distribution_curve(antibiotic=drug,bins=15, save_path=data_locations['distribution_curve_without_outliers'], remove_outliers=3,error_path=data_locations['error_path'])

        data_locations['Mean_MIC_trend_without_sd'] = processing_data.antibiotic_trend_analysis(antibiotic=drug, save_path=data_locations['Mean_MIC_trend_without_sd'],include_sd=False,error_path=data_locations['error_path'])
        data_locations['Mean_MIC_trend_without_sd_remove_outliers'] = processing_data.antibiotic_trend_analysis(antibiotic=drug, save_path=data_locations['Mean_MIC_trend_without_sd_remove_outliers'],remove_outliers=3, include_sd=False,error_path=data_locations['error_path'])
        data_locations['Mean_MIC_trend_with_sd_remove_outliers'] = processing_data.antibiotic_trend_analysis(antibiotic=drug, save_path=data_locations['Mean_MIC_trend_with_sd_remove_outliers'], remove_outliers=3,error_path=data_locations['error_path'])
        data_locations['Mean_MIC_trend_with_sd'] = processing_data.antibiotic_trend_analysis(antibiotic=drug, save_path=data_locations['Mean_MIC_trend_with_sd'],error_path=data_locations['error_path'])
        data_locations['total_isolates'] = processing_data.total_isolates_over_time(antibiotic=drug, save_path=data_locations['total_isolates'],error_path=data_locations['error_path'])
        #timeseries_as_dict = processing_data.antibiotic_timeseries(antibiotic=drug, intervals='3M').to_dict()
        #timeseries_json_ready = {}
        #Change timeseries date index to string
        #for key, val in timeseries_as_dict.items():
        #    timeseries_json_ready[key] = dict(map(lambda kv: (str(kv[0])[0:10], kv[1]), val.items()))
        
        #json_obj = json.dumps(timeseries_json_ready)
        #with open(data_locations['timeseries'], 'wb') as file:
        #  file.write(json_obj)

    return data_locations
    
def mkdir_p(path):
    try:
        os.makedirs(path, mode=0o777)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

def read_in():
    lines = sys.stdin.readlines()
    return json.loads(lines[0])

def shred_string(x):
    if type(x) == dict:
        new_dict = {}
        if 'error' in x.keys():
            return x
        for key, value in x.items():
            try:
                new_dict[key] = value.split('user_data')[1]
            except:
                new_dict[key] = value.split('public')[1]
        return new_dict
    else:
        return x.split('user_data')[1]

def remove_drugs(df):
    new_df = df.copy()
    for col in df:
        if pd.isnull(df[col]).sum() > (df.shape[0]*0.95):
            new_df.drop(col, axis=1)
    return new_df

if __name__ == '__main__':
    
    #myargs = getopts(sys.argv)
    #myargs = read_in()
    #myargs = json.load(sys.stdin.readlines(), encoding='utf-8')
    myargs = json.loads(sys.argv[1])[0]
    if 'dbname' in myargs.keys():
        dbname = myargs['dbname']
    else:
        print("Please specify database name e.g '-dbname database1'")
        sys.exit()

    if 'bug' in myargs.keys():
        bug = myargs['bug']
    else:
        print("Please specify target organism")
        sys.exit()

    if 'start_date' in myargs.keys() and 'end_date' in myargs.keys():
        start_date = myargs['start_date']
        end_date = myargs['end_date']
    else:
        start_date = None
        end_date = None
    
    if 'antibiotic' in myargs.keys():
        drug = myargs['antibiotic']
    else:
        drug = None


    user_id = myargs['userID']
    if start_date != None and end_date != None:
      save_path = '/home/rossco/Documents/web_projects/microbiology_data_portal/user_data/{}/{}_{}_{}/'.format(user_id, bug, start_date, end_date)
    else:
      save_path = '/home/rossco/Documents/web_projects/microbiology_data_portal/user_data/{}/{}/'.format(user_id, bug)
    pickle_file = "{}{}.pickle".format(save_path, bug)

    data_locations = {
            'descriptive_stats': "{}{}/descriptive_stats.json".format(save_path, drug),
            'distribution_curve_raw': "{}{}/figures/distribution.png".format(save_path,drug),
            'distribution_curve_without_outliers': "{}{}/figures/distribution_without_outliers.png".format(save_path,drug),
            'Mean_MIC_trend_without_sd': "{}{}/figures/MIC_Trend_without_SD.png".format(save_path,drug),
            'Mean_MIC_trend_without_sd_remove_outliers': "{}{}/figures/MIC_Trend_without_SD_remove_outliers.png".format(save_path,drug),
            'Mean_MIC_trend_with_sd_remove_outliers': "{}{}/figures/MIC_Trend_with_SD_remove_outliers.png".format(save_path,drug),
            'correlation_matrix': "{}correlation_matrix.png".format(save_path),
            'excel_data': "{}all_mic_data.xlsx".format(save_path),
            'timeseries': "{}timeseries.json".format(save_path),
            'total_isolates': "{}{}/figures/total_isolates.png".format(save_path,drug),
            'Mean_MIC_trend_with_sd': "{}{}/figures/MIC_Trend_with_SD.png".format(save_path,drug),
            'error_path': "/home/rossco/Documents/web_projects/microbiology_data_portal/public/img/broken_robot.png"
            }
            
    if drug:
        if os.path.exists(save_path):
            if os.path.exists('{}{}/'.format(save_path, drug)):
                #Load previous results
                print(json.dumps(shred_string(data_locations)))
                sys.exit()
            else:
                mkdir_p("{}{}/".format(save_path, drug))
                mkdir_p("{}{}/figures/".format(save_path, drug))
                print(json.dumps(shred_string(create_figures(myargs, save_path, pickle_file, start_date, end_date))))
        else:
            mkdir_p(save_path)
            mkdir_p("{}{}/".format(save_path, drug))
            mkdir_p("{}{}/figures/".format(save_path, drug))
            client = pymongo.MongoClient()
            extract = ExtractData(db_name=dbname, mongo_client=client)
            bug_data = extract.get_mic_data(organism=bug)
            file_name = '{}.pickle'.format(bug)
            extract.to_pickle(mic_data=bug_data, path=save_path, filename=file_name)
            print(json.dumps(shred_string(create_figures(myargs, save_path, pickle_file, start_date,end_date))))
            processing_data = ProcessData(pickle_file, start_date=start_date, end_date=end_date)
            print(json.dumps(shred_string(processing_data.to_excel(path=data_locations['excel_data']))))
            print(json.dumps(shred_string(processing_data.correlation_matrix(save_path=data_locations['correlation_matrix'], error_path=data_locations['error_path']))))
            sys.exit()
    else:
        if os.path.exists(save_path):
            org_df = ProcessData(pickle_file, start_date=start_date, end_date=end_date).get_dataframe()
            org_df = remove_drugs(org_df)
            relevant_antibiotics = org_df.columns.tolist()
            relevant_antibiotics.remove('species')
            timeseries = ProcessData
            print(json.dumps({
                'correlation_matrix': shred_string("{}correlation_matrix.png".format(save_path)),
                'excel_data': shred_string("{}all_mic_data.xlsx".format(save_path)),
                'relevant_antibiotics': relevant_antibiotics
            }))
            sys.exit()
        else:
            mkdir_p(save_path)
            client = pymongo.MongoClient()
            extract = ExtractData(db_name=dbname, mongo_client=client)
            bug_data = extract.get_mic_data(organism=bug)
            file_name = '{}.pickle'.format(bug)
            extract.to_pickle(mic_data=bug_data, path=save_path, filename=file_name)
            processing_data = ProcessData(pickle_file, start_date=start_date, end_date=end_date)
            processing_data.to_excel(path=data_locations['excel_data'])
            processing_data.correlation_matrix(save_path=data_locations['correlation_matrix'], error_path=data_locations['error_path'])
            org_df = ProcessData(pickle_file, start_date=start_date, end_date=end_date).get_dataframe()
            org_df = remove_drugs(org_df)
            relevant_antibiotics = org_df.columns.tolist()
            relevant_antibiotics.remove('species')
            print(json.dumps({
                'correlation_matrix': shred_string("{}correlation_matrix.png".format(save_path)),
                'excel_data': shred_string("{}all_mic_data.xlsx".format(save_path)),
                'relevant_antibiotics': relevant_antibiotics
            }))
            sys.exit()
    
