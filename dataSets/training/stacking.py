#coding=utf-8
import pandas as pd
import numpy as np
from scipy.stats import skew
from sklearn.cross_validation import KFold
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error
from sklearn.linear_model import Ridge, RidgeCV, ElasticNet, LassoCV, Lasso, LinearRegression
from math import sqrt
from pandas.tseries.offsets import *
import random
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import AdaBoostRegressor
import xgboost as xgb
from sklearn.model_selection import GridSearchCV
from xgboost.sklearn import XGBRegressor
from sklearn.externals import joblib

'''
待优化点：
1. 在stack里加一个均值模型
2. 在stack里加Adaboost套liner模型，Adaboost套DecisionTree模型
'''

TARGET = 'y'
NFOLDS = 5
SEED = 0
NROWS = None

id_direction_lst = [("1S", "entry"), ("1S", "exit"), ("2S", "entry"), ("3S", "entry"), ("3S", "exit")]
# id_direction_lst = [("1S", "exit")]
tuple_lst = []
for id, direction in id_direction_lst:
   for i in range(6):
       tuple_lst.append((id, direction, i, "morning"))
       tuple_lst.append((id, direction, i, "afternoon"))
# tuple_lst = [("1S", "entry", 1)]

et_params = {
        'n_jobs': 16,
        'n_estimators': 1000,
        'max_features': 0.5,
        'max_depth': 5,
        'min_samples_leaf': 10,
    }

et_params_cv = [{
    'n_jobs': [16],
    'n_estimators': [1000],#[600 + i * 100 for i in range(6)],
    'max_features': [0.5 + i * 0.1 for i in range(3)],
    'max_depth': [4, 5],
    'min_samples_leaf': [2]
}]

rf_params = {
        'n_jobs': 16,
        'n_estimators': 1000,
        'max_features': 0.2,
        'max_depth': 5,
        'min_samples_leaf': 10,
     }

rf_params_cv = [{
    'n_jobs': [16],
    'n_estimators': [1000], #[600 + i * 100 for i in range(6)],
    'max_features': [0.5 + i * 0.1 for i in range(3)],
    'max_depth': [4, 5],
    'min_samples_leaf': [2]
}]

rd_params = {
        'alpha': 10
    }

rd_params_cv = [{
    'alpha': [10 + i * 5 for i in range(10)]
}]

ls_params = {
        'alpha': 0.002,
        'max_iter': 5000
    }

ls_params_cv = [{
    'alpha': [0.002 + 0.001 * i for i in range(10)],
    'max_iter': [5000]
}]

gbdt_params = {
    'max_depth': 4,
    'min_samples_leaf': 10,
    'learning_rate': 0.1,
    'loss': 'lad',
    'n_estimators': 3000,
    'max_features': 1.0
    }

gbdt_params_cv = [{
    'max_depth': [4, 5],
    'min_samples_leaf': [1],
    'learning_rate': [0.1],#[0.08 + i * 0.01 for i in range(3)],
    'loss': ['lad'],
    'n_estimators': [3000],
    'max_features': [0.7 + i * 0.1 for i in range(4)]
}]

gbdt_params2 = {
    'max_depth': 4,
    'min_samples_leaf': 1,
    'learning_rate': 0.3,
    'loss': 'lad',
    'n_estimator': 3000,
    'max_features': 0.7
}

xgb_params = {
    'seed': 0,
    'colsample_bytree': 0.7,
    'silent': 1,
    'subsample': 0.7,
    'learning_rate': 0.1,
    'objective': 'reg:linear',
    'max_depth': 5,
    # 'num_parallel_tree': 1,
    'min_child_weight': 1,
    # 'eval_metric': 'rmse',
    'n_estimators': 2000
}

xgb_params_cv = [{
    'seed': [0],
    'colsample_bytree': [0.7],
    'silent': [1],
    'subsample': [0.7 + i * 0.1 for i in range(3)],
    'learning_rate': [0.1], #[0.08 + i * 0.01 for i in range(5)],
    'objective': ['reg:linear'],
     'max_depth': [4, 5],
    'min_child_weight': [1],
    'n_estimators': [2000]
}]

xgb_params2 = {
    'seed': 0,
    'colsample_bytree': 0.7,
    'silent': 1,
    'subsample': 0.7,
    'learning_rate': 0.03,
    'objective': 'reg:linear',
    'max_depth': 5,
    # 'num_parallel_tree': 1,
    'min_child_weight': 1,
    # 'eval_metric': 'rmse',
    'n_estimators': 2000,
    'reg_lambda': 0.3
}

xgb_params2_cv = [{
    'seed': [0],
    'colsample_bytree': [0.7],
    'silent': [1],
    'subsample': [0.7 + i * 0.1 for i in range(3)],
    'learning_rate': [0.03],#[0.03 + i * 0.01 for i in range(5)],
    'objective': ['reg:linear'],
    'max_depth': [4, 5],
    'min_child_weight': [1],
    'n_estimators': [2000],
    'reg_lambda': [0.3]
}]

ada_param = {
    'base_estimator': DecisionTreeRegressor(max_depth=4),
    'n_estimators': 300
}

ada_param_cv = [{
    'base_estimator': [DecisionTreeRegressor(max_depth=4)],
    'n_estimators': [200 + i * 50 for i in range(6)]
}]

ada_param2 = {
    'base_estimator': LinearRegression(),
    'n_estimators': 300
}

mean_param = {

}

model_score_dic = {}

model_used_name = ["GB", "RF", "XGB", "XGB2", "LS", "ET", "RD"]


# 还原历史最好成绩的
def predict0(tollgate_id, direction, offset):
    ## Load the data ##
    train_file = "./train&test0_zjw/volume_" + direction + "_train_" + tollgate_id + "offset" + str(offset) + ".csv"
    train = pd.read_csv(train_file, index_col="Unnamed: 0")
    # train = train.dropna()
    train["time"] = train.index
    train["time"] = train["time"].apply(pd.Timestamp)
    train = train[(train["time"] < pd.Timestamp("2016-09-30 22:20:00")) |
                  (train["time"] > pd.Timestamp("2016-10-07 01:20:00"))]
    del train["time"]
    train = train.fillna(0)
    test_file = "./train&test0_zjw/volume_" + direction + "_test_" + tollgate_id + "offset" + str(offset) + ".csv"
    test = pd.read_csv(test_file, index_col="Unnamed: 0")
    test_index = test.index
    print "predict1 path of train file: " + train_file
    print "predict1 path of test file: " + test_file

    ## Preprocessing ##

    y_train = np.log1p(train[TARGET])

    train.drop([TARGET], axis=1, inplace=True)

    all_data = pd.concat((train.copy(), test.copy()))

    # log transform skewed numeric features:
    numeric_feats = all_data.dtypes[all_data.dtypes != "object"].index

    skewed_feats = train[numeric_feats].apply(lambda x: skew(x.dropna()))  # compute skewness
    skewed_feats = skewed_feats[skewed_feats > 0.75]
    skewed_feats = skewed_feats.index

    all_data[skewed_feats] = np.log1p(all_data[skewed_feats])

    stdSc = StandardScaler()
    all_data[numeric_feats] = stdSc.fit_transform(all_data[numeric_feats])

    all_data = pd.get_dummies(all_data)

    # creating matrices for sklearn:

    x_train = all_data[:train.shape[0]]
    x_test = all_data[train.shape[0]:]

    def gbdt_model(X_train, X_test, y_train):
        best_rate = 0.1
        best_n_estimator = 3000
        # param_grid = [
        #     {'max_depth': [3], 'min_samples_leaf': [10],
        #      'learning_rate': [best_rate + 0.01 * i for i in range(-2, 4, 1)],
        #      'loss': ['lad'],
        #      'n_estimators': [best_n_estimator + i * 200 for i in range(-2, 3, 1)],
        #      'max_features': [1.0]}
        # ]
        param_grid = [
            {'max_depth': [3],
             'min_samples_leaf': [10],
             'learning_rate': [0.1],
             'loss': ['lad'],
             'n_estimators': [3000],
             'max_features': [1.0]
             }
        ]

        # 这是交叉验证的评分函数
        def scorer(estimator, X, y):
            predict_arr = estimator.predict(X)
            y_arr = y
            result = (np.abs(1 - np.exp(predict_arr - y_arr))).sum() / len(y)
            return result

        model = GradientBoostingRegressor()
        clf = GridSearchCV(model, param_grid, refit=True, scoring=scorer)

        clf.fit(X_train, y_train)
        params = pd.DataFrame()
        params["importance"] = clf.best_estimator_.feature_importances_
        params.index = X_train.columns
        params = params.sort_values(["importance"], ascending=False)
        params.to_csv("./train&test0_zjw/features_importances_" + direction + "_" + tollgate_id + "_offset" + str(offset) + ".csv")
        print "Best GBDT param is :", clf.best_params_
        print "sroce is :", scorer(clf.best_estimator_, X_train, y_train)
        return clf.predict(X_test)

    def features_filter(X_train, y_train):
        columns = X_train.columns

        def scorer(data_lst1, data_lst2):
            return (np.abs(1 - np.exp(data_lst1 - data_lst2))).mean()

        param = {'max_depth': 5,
                 'min_samples_leaf': 10,
                 'learning_rate': 0.1,
                 'loss': 'lad',
                 'n_estimators': 3000,
                 'max_features': 1.0}
        scores = []
        for column in columns:
            model = GradientBoostingRegressor(**param)
            train_temp = X_train[column].reshape(-1, 1)
            model.fit(train_temp, y_train)
            result = model.predict(train_temp)
            scores.append(scorer(result, y_train))
        column_score = [[scores[i], columns[i]] for i in range(len(scores))]
        column_score.sort(key=(lambda x: x[0]), reverse=True)
        dupli_scores = []
        used_cols = []
        for score, column in column_score:
            model = GradientBoostingRegressor(**param)
            used_cols.append(column)
            train_temp = X_train[used_cols]
            model.fit(train_temp, y_train)
            result = model.predict(train_temp)
            dupli_scores.append(scorer(result, y_train))
        min_score = 100
        min_index = 0
        for i in range(len(dupli_scores)):
            score = dupli_scores[i]
            if score < min_score:
                min_score = score
                min_index = i

        result = [column_score[index][1] for index in range(min_index + 1)]
        return result


    def gbdt_filter(X_train, y_train):
        param = {'max_depth': 3,
                 'min_samples_leaf': 10,
                 'learning_rate': 0.1,
                 'loss': 'lad',
                 'n_estimators': 750,
                 'max_features': 1.0}
        model = GradientBoostingRegressor(**param)
        model.fit(X_train, y_train)
        result = model.predict(X_train)
        X_train["score"] = np.abs(y_train.copy() - result.copy()) / (1 + y_train.copy())
        X_train = X_train.sort_values(by="score")
        split = int(X_train.shape[0] * 0.90)
        print "use %d lines of original training set" % (split, )
        del X_train["score"]
        return X_train.iloc[range(split), :], y_train.iloc[range(split)]

    # x_train, y_train = gbdt_filter(x_train, y_train)
    # index = features_filter(x_train, y_train)
    # print index
    # x_train = x_train[index]
    # x_test = x_test[index]

    return gbdt_model(x_train, x_test, y_train), test_index


def predict1(tollgate_id, direction, offset, time_period):
    ## Load the data ##
    # train_file = "./train&test_zjw/volume2_" + direction + "_train_" + tollgate_id + \
    #              "_offset_" + str(offset) + "_" + time_period + ".csv"
    # train1_file = "./train&test_zjw/volume_" + direction + "_train_" + tollgate_id + \
    #              "_offset_" + str(offset) + "_" + time_period + ".csv"
    # train_phase1 = pd.read_csv(train1_file, index_col="Unnamed: 0")
    # train = pd.read_csv(train_file, index_col="Unnamed: 0")
    # print "shape before merge : " + str(train.shape)
    # train = train.append(train_phase1)
    # train.index = range(train.shape[0])
    # print "shape after merge : " + str(train.shape)
    train_file = "./train&test1_zjw/volume_" + direction + "_train_" + tollgate_id + \
                      "_offset_" + str(offset) + "_" + time_period + ".csv"
    train = pd.read_csv(train_file, index_col="Unnamed: 0")
    train.index = range(train.shape[0])
    del train["time"]

    test_file = "./train&test1_zjw/volume_" + direction + "_test_" + tollgate_id + \
                "_offset_" + str(offset) + "_" + time_period + ".csv"
    test = pd.read_csv(test_file, index_col="Unnamed: 0")
    print "predict1 path of train file: " + train_file
    print "predict1 path of test file: " + test_file
    # 训练集中有两种空值，一种是删除了10月1日到10月7日的车辆记录后，resample出现的空值；另一种是20分钟没有车辆的那种空值
    # train = train.dropna()
    # train["time"] = train.index
    # train["time"] = train["time"].apply(pd.Timestamp)
    # train = train[(train["time"] < pd.Timestamp("2016-09-30 22:20:00")) |
    #               (train["time"] > pd.Timestamp("2016-10-07 01:20:00"))]
    # del train["time"]
    train = train.fillna(0)

    test_index = test["time"].copy()
    del test["time"]

    ## Preprocessing ##

    y_train = np.log1p(train[TARGET])

    train.drop([TARGET], axis=1, inplace=True)

    all_data = pd.concat((train.copy(), test.copy()))

    # log transform skewed numeric features:
    numeric_feats = all_data.dtypes[all_data.dtypes != "object"].index

    skewed_feats = train[numeric_feats].apply(lambda x: skew(x.dropna()))  # compute skewness
    skewed_feats = skewed_feats[skewed_feats > 0.75]
    skewed_feats = skewed_feats.index

    all_data[skewed_feats] = np.log1p(all_data[skewed_feats])

    # stdSc = StandardScaler()
    # all_data[numeric_feats] = stdSc.fit_transform(all_data[numeric_feats])

    all_data = pd.get_dummies(all_data)

    # creating matrices for sklearn:

    x_train = all_data[:train.shape[0]]
    x_test = all_data[train.shape[0]:]

    std_sc = StandardScaler()
    x_train[numeric_feats] = std_sc.fit_transform(x_train[numeric_feats])
    x_test[numeric_feats] = std_sc.transform(x_test[numeric_feats])

    x_train = np.array(x_train)
    x_test = np.array(x_test)

    ntrain = x_train.shape[0]
    ntest = x_test.shape[0]

    kf = KFold(ntrain, n_folds=NFOLDS, shuffle=True, random_state=SEED)

    class Mean_Model(object):
        def __init__(self, random_state=None):
            pass

        def fit(self, X_train, y_train):
            pass

        def predict(self, X_test):
            volume_index = ["volume0", "volume1", "volume2", "volume3", "volume4", "volume5"]
            result = np.zeros(len(X_test))
            for index in volume_index:
                result += np.log1p(X_test.loc[:, index].values)
            result /= len(volume_index)
            return result

    class SklearnWrapper(object):
        def __init__(self, clf, name, seed=0, params=None):
            # params['random_state'] = seed
            self.clf = clf(**params)
            self.name = name
            self.file_name = None

        def train(self, x_train, y_train):
            self.clf.fit(x_train, y_train)
            # self.file_name = "train&test_zjw/model/" + self.name + "_" + tollgate_id + "_" + direction + "_%d.model" % (offset, )
            # joblib.dump(self.clf, self.file_name, compress=3)

        def predict(self, x):
            # model = joblib.load(self.file_name)
            # return model.predict(x)
            return self.clf.predict(x)

        def clf_type(self):
            return type(self.clf)

    class SklearnWrapper_cv(object):
        def scorer(self, estimator, X, y):
            predict_arr = estimator.predict(X)
            y_arr = y
            result = (np.abs(1 - np.exp(predict_arr - y_arr))).sum() / len(y)
            return result

        def __init__(self, clf, name, seed=0, params=None):
            # params['random_state'] = seed
            model = clf()
            self.clf = GridSearchCV(estimator=model, param_grid=params, refit=True, scoring=self.scorer)
            self.name = name
            self.file_name = None

        def train(self, x_train, y_train, stack_idx):
            # print x_train
            self.clf.fit(x_train, y_train)
            self.file_name = "train&test_zjw/model/" + self.name + "_" + tollgate_id + "_" + direction + "_%d_%d.plk" % (offset, stack_idx)
            print self.file_name
            joblib.dump(self.clf.best_estimator_, self.file_name, compress=3)

        def predict(self, x):
            model = joblib.load(self.file_name)
            return model.predict(x)

        def clf_type(self):
            return type(self.clf)

    class XgbWrapper(object):
        def __init__(self, name, seed=0, params=None):
            self.param = params
            self.param["seed"] = seed
            self.nrounds = params.pop("nrounds", 250)
            self.name = name
            self.file_name = None
            self.gbdt = None

        def train(self, x_train, y_train):
            dtrain = xgb.DMatrix(x_train, label=y_train)
            self.gbdt = xgb.train(self.param, dtrain, self.nrounds)
            # self.file_name = "train&test_zjw/model/" + self.name + "_" + tollgate_id + "_" + direction + "_%d.model" % (offset, )
            # joblib.dump(self.gbdt, self.file_name, compress=3)

        def predict(self, x):
            # model = joblib.load(self.file_name)
            # return model.predict(xgb.DMatrix(x))
            return self.gbdt.predict(xgb.DMatrix(x))

        def clf_type(self):
            return None

    class XgbWrapper_cv(object):
        def __init__(self, name, seed=0, params=None):
            # self.param = params
            # self.param["seed"] = seed
            # self.nrounds = params.pop("nrounds", 250)
            gbdt = XGBRegressor()
            self.model = GridSearchCV(gbdt, params, refit=True)
            self.name = name
            self.file_name = None

        def train(self, x_train, y_train, stack_idx):
            #dtrain = xgb.DMatrix(x_train, label=y_train)
            self.model.fit(x_train, y_train)
            self.file_name = "train&test_zjw/model/" + self.name + "_" + tollgate_id + "_" + direction + "_%d_%d.model" % (offset, stack_idx)
            joblib.dump(self.model, self.file_name, compress=3)

        def predict(self, x):
            model = joblib.load(self.file_name)
            return model.predict(x)
            #return self.model.predict(xgb.DMatrix(x))

        def clf_type(self):
            return None

    def get_oof(clf):
        oof_train = np.zeros((ntrain,))
        oof_test = np.zeros((ntest,))
        oof_test_skf = np.empty((NFOLDS, ntest))
        idx = 0
        for i, (train_index, test_index) in enumerate(kf):
            x_tr = x_train[train_index]
            y_tr = y_train[train_index]
            x_te = x_train[test_index]

            if clf.clf_type() and clf.clf_type() == Mean_Model:
                oof_train = clf.predict(train.copy())
                oof_test_skf[i, :] = clf.predict(test.copy())
            else:
                clf.train(x_tr, y_tr)

                oof_train[test_index] = clf.predict(x_te)
                oof_test_skf[i, :] = clf.predict(x_test)
                idx += 1

        oof_test[:] = oof_test_skf.mean(axis=0)
        # print oof_train
        # print oof_test
        return oof_train.reshape(-1, 1), oof_test.reshape(-1, 1)

    # 可以无限增加元模型，然后增加模型组合的可能性
    model_name_lst = ["GB", "RF", "XGB", "XGB2", "LS", "ET", "RD"]
    model_lst = [GradientBoostingRegressor, RandomForestRegressor, XGBRegressor, XGBRegressor,
                 Lasso, ExtraTreesRegressor, Ridge]
    model_params = [gbdt_params, rf_params, xgb_params, xgb_params2,
                  ls_params, et_params, rd_params]
    # model_params = [gbdt_params_cv, rf_params_cv, xgb_params_cv, xgb_params2_cv,
    #                 ls_params_cv, et_params_cv, rd_params_cv]
    model2_name = ["GB", "XGB", "XGB2"]
    model2_lst = [GradientBoostingRegressor, XGBRegressor, XGBRegressor]
    model2_params = [gbdt_params, xgb_params, xgb_params2]
    model_used_idx = [#[0, 1, 2],
                      #[0, 1, 2, 3],
                      #[0, 1, 2, 3, 4],
                      [0, 1, 2, 3, 4, 5],
                      [0, 1, 2, 3, 4, 5, 6],
                      [1, 2, 3, 4, 5, 6],
                      #[2, 3, 4, 5, 6],
                      #[3, 4, 5, 6],
                      #[4, 5, 6]]
        ]

    y_test = np.zeros((ntest,))
    for i in range(len(model_used_idx)):

        def generate_wrapper(index, names, models, params, cv=True):
            # print names[index]
            if names[index] == "XGB" or names[index] == "XGB2":
                if cv:
                    return XgbWrapper_cv(name=names[index], seed=SEED, params=params[index])
                else:
                    return XgbWrapper(name=names[index], seed=SEED, params=params[index])
            else:
                if cv:
                    return SklearnWrapper_cv(name=names[index], clf=models[index], seed=SEED, params=params[index])
                else:
                    return SklearnWrapper(name=names[index], clf=models[index], seed=SEED, params=params[index])

        # model_used = [model_lst[idx] for idx in model_used_idx[i]]
        # params_used = [model_params[idx] for idx in model_used_idx[i]]
        # wrapper_lst = [SklearnWrapper(clf=model_used[i], seed=SEED, params=params_used[i])
        #                for i in range(len(model_used))]
        wrapper_lst = [generate_wrapper(idx, model_name_lst, model_lst, model_params, cv=False)
                       for idx in range(len(model_used_idx[i]))]
        train_test_lst = [get_oof(wrapper) for wrapper in wrapper_lst]
        train_lst = [train_temp for train_temp, test_temp in train_test_lst]
        test_lst = [test_temp for train_temp, test_temp in train_test_lst]

        def scorer(data_lst1, data_lst2):
            # print data_lst1
            # print data_lst2
            return (np.abs(1 - np.exp(data_lst1.values - data_lst2.reshape((1, -1))[0]))).mean()

        for j in range(len(train_lst)):
            score = scorer(y_train, train_lst[j])
            print model_name_lst[j] + "-CV".format(score)
            if model_name_lst[j] in model_score_dic:
                model_score_dic[model_name_lst[j]][0] += score
                model_score_dic[model_name_lst[j]][1] += 1
            else:
                model_score_dic[model_name_lst[j]] = [score, 1]
        x_train = np.concatenate(train_lst, axis=1)
        x_test = np.concatenate(test_lst, axis=1)

        print("{},{}".format(x_train.shape, x_test.shape))

        # random_index = random.randint(0, 2)
        random_index = i
        print "second floor use : " + model2_name[random_index]
        # model2_param = model2_params[random_index]
        # model2 = model2_lst[random_index](**model2_param)
        model2 = generate_wrapper(random_index, model2_name, model2_lst, model2_params, cv=False)
        model2.train(x_train, y_train)
        y_test += model2.predict(x_test)
    return y_test, len(model_used_idx), test_index


def predict2(tollgate_id, direction, offset):
    index_cols = ["tollgate_id", "direction", "time"]
    ## Load the data ##
    train_file = "./train&test5_zjw/volume_" + direction + "_train_" + tollgate_id + ".csv"
    train = pd.read_csv(train_file, index_col="time")
    test_file = "./train&test5_zjw/volume_" + direction + "_test_" + tollgate_id + "offset" + str(offset) + ".csv"
    test = pd.read_csv(test_file, index_col="time")
    print "predict2 path of train file: " + train_file
    print "predict2 path of test file: " + test_file
    train = train.dropna()
    test_index = test.index

    ## Preprocessing ##

    y_train = np.log(train[TARGET] + 1)

    train.drop([TARGET], axis=1, inplace=True)

    all_data = pd.concat((train.copy(), test.copy()))

    # log transform skewed numeric features:
    numeric_feats = all_data.dtypes[all_data.dtypes != "object"].index

    skewed_feats = train[numeric_feats].apply(lambda x: skew(x.dropna()))  # compute skewness
    skewed_feats = skewed_feats[skewed_feats > 0.75]
    skewed_feats = skewed_feats.index

    all_data[skewed_feats] = np.log1p(all_data[skewed_feats])

    stdSc = StandardScaler()
    all_data[numeric_feats] = stdSc.fit_transform(all_data[numeric_feats])

    all_data = pd.get_dummies(all_data)

    # filling NA's with the mean of the column:

    # creating matrices for sklearn:

    x_train = np.array(all_data[:train.shape[0]])
    x_test = np.array(all_data[train.shape[0]:])

    ntrain = x_train.shape[0]
    ntest = x_test.shape[0]

    kf = KFold(ntrain, n_folds=NFOLDS, shuffle=True, random_state=SEED)

    class Mean_Model(object):
        def __init__(self, random_state=None):
            pass

        def fit(self, X_train, y_train):
            pass

        def predict(self, X_test):
            volume_index = ["volume0", "volume1", "volume2", "volume3", "volume4", "volume5"]
            result = np.zeros(len(X_test))
            for index in volume_index:
                result += np.log1p(X_test.loc[:, index].values)
            result /= len(volume_index)
            return result

    class SklearnWrapper(object):
        def __init__(self, clf, seed=0, params=None):
            params['random_state'] = seed
            self.clf = clf(**params)

        def train(self, x_train, y_train):
            self.clf.fit(x_train, y_train)

        def predict(self, x):
            return self.clf.predict(x)

        def clf_type(self):
            return type(self.clf)

    class XgbWrapper(object):
        def __init__(self, seed=0, params=None):
            self.param = params
            self.param["seed"] = seed
            self.nrounds = params.pop("nrounds", 250)

        def train(self, x_train, y_train):
            dtrain = xgb.DMatrix(x_train, label=y_train)
            self.gbdt = xgb.train(self.param, dtrain, self.nrounds)

        def predict(self, x):
            return self.gbdt.predict(xgb.DMatrix(x))

        def clf_type(self):
            return None

    def get_oof(clf):
        oof_train = np.zeros((ntrain,))
        oof_test = np.zeros((ntest,))
        oof_test_skf = np.empty((NFOLDS, ntest))

        for i, (train_index, test_index) in enumerate(kf):
            x_tr = x_train[train_index]
            y_tr = y_train[train_index]
            x_te = x_train[test_index]

            if clf.clf_type() and clf.clf_type() == Mean_Model:
                oof_train = clf.predict(train.copy())
                oof_test_skf[i, :] = clf.predict(test.copy())
            else:
                clf.train(x_tr, y_tr)

                oof_train[test_index] = clf.predict(x_te)
                oof_test_skf[i, :] = clf.predict(x_test)

        oof_test[:] = oof_test_skf.mean(axis=0)
        # print oof_train
        # print oof_test
        return oof_train.reshape(-1, 1), oof_test.reshape(-1, 1)

    model_name = ["GB", "RF", "XGB", "XGB2", "ADA", "ET"]
    model_lst = [GradientBoostingRegressor, RandomForestRegressor, None, None,
                 AdaBoostRegressor, ExtraTreesRegressor]
    model_params = [gbdt_params, rf_params, xgb_params, xgb_params2, ada_param, et_params]
    model2_name = ["GB", "ADA", "XGB", "XGB2"]
    model2_lst = [GradientBoostingRegressor, AdaBoostRegressor, None, None]
    model2_params = [gbdt_params, ada_param, xgb_params, xgb_params2]
    model_used_idx = [[0, 1, 2],
                      [0, 1, 2, 3],
                      [0, 1, 2, 3, 4],
                      [0, 1, 2, 3, 4, 5],
                      [1, 2, 3, 4, 5],
                      [2, 3, 4, 5],
                      [3, 4, 5]]

    y_test = np.zeros((ntest,))
    for i in range(len(model_used_idx)):

        def generate_wrapper(index, names, models, params):
            if names[index] == "XGB" or names[index] == "XGB2":
                return XgbWrapper(seed=SEED, params=params[index])
            else:
                return SklearnWrapper(clf=models[index], seed=SEED, params=params[index])

        # model_used = [model_lst[idx] for idx in model_used_idx[i]]
        # arams_used = [model_params[idx] for idx in model_used_idx[i]]
        wrapper_lst = [generate_wrapper(idx, model_name, model_lst, model_params)
                       for idx in range(len(model_used_idx[i]))]
        train_test_lst = [get_oof(wrapper) for wrapper in wrapper_lst]
        train_lst = [train_temp for train_temp, test_temp in train_test_lst]
        test_lst = [test_temp for train_temp, test_temp in train_test_lst]

        def scorer(data_lst1, data_lst2):
            # print data_lst1
            # print data_lst2
            return (np.abs(1 - np.exp(data_lst1.values - data_lst2.reshape((1, -1))[0]))).mean()

        for j in range(len(train_lst)):
            score = scorer(y_train, train_lst[j])
            print model_name[j] + "-CV".format(score)
            if model_name[j] in model_score_dic:
                model_score_dic[model_name[j]][0] += score
                model_score_dic[model_name[j]][1] += 1
            else:
                model_score_dic[model_name[j]] = [score, 1]
        x_train = np.concatenate(train_lst, axis=1)
        x_test = np.concatenate(test_lst, axis=1)

        print("{},{}".format(x_train.shape, x_test.shape))

        random_index = random.randint(0, 3)
        print "second floor use : " + model2_name[random_index]
        model2 = generate_wrapper(random_index, model2_name, model2_lst, model2_params)
        model2.train(x_train, y_train)
        y_test += model2.predict(x_test)
    return y_test, len(model_used_idx), test_index


# 不区分端口和方向，纯时间特征
def predict3(offset):
    ## Load the data ##
    train = pd.read_csv("./train&test3_zjw/train_offset" + str(offset) + ".csv", index_col="Unnamed: 0")
    test = pd.read_csv("./train&test3_zjw/test_offset" + str(offset) + ".csv", index_col="Unnamed: 0")
    train = train.dropna()
    test_index = pd.Series(test.index + "-" + test["direction"] + "-" + str(offset))
    test_tollgate = test.tollgate_id.values
    test_direction = test.direction.values


    ## Preprocessing ##

    y_train = np.log(train[TARGET] + 1)

    train.drop([TARGET], axis=1, inplace=True)

    all_data = pd.concat((train.copy(), test.copy()))

    # log transform skewed numeric features:
    numeric_feats = all_data.dtypes[all_data.dtypes != "object"].index

    skewed_feats = train[numeric_feats].apply(lambda x: skew(x.dropna()))  # compute skewness
    skewed_feats = skewed_feats[skewed_feats > 0.75]
    skewed_feats = skewed_feats.index

    all_data[skewed_feats] = np.log1p(all_data[skewed_feats])

    stdSc = StandardScaler()
    all_data[numeric_feats] = stdSc.fit_transform(all_data[numeric_feats])

    all_data = pd.get_dummies(all_data)

    # filling NA's with the mean of the column:

    # creating matrices for sklearn:

    x_train = np.array(all_data[:train.shape[0]])
    x_test = np.array(all_data[train.shape[0]:])

    ntrain = x_train.shape[0]
    ntest = x_test.shape[0]

    kf = KFold(ntrain, n_folds=NFOLDS, shuffle=True, random_state=SEED)

    class Mean_Model(object):
        def __init__(self, random_state=None):
            pass

        def fit(self, X_train, y_train):
            pass

        def predict(self, X_test):
            volume_index = ["volume0", "volume1", "volume2", "volume3", "volume4", "volume5"]
            result = np.zeros(len(X_test))
            for index in volume_index:
                result += np.log1p(X_test.loc[:, index].values)
            result /= len(volume_index)
            return result

    class SklearnWrapper(object):
        def __init__(self, clf, seed=0, params=None):
            params['random_state'] = seed
            self.clf = clf(**params)

        def train(self, x_train, y_train):
            self.clf.fit(x_train, y_train)

        def predict(self, x):
            return self.clf.predict(x)

        def clf_type(self):
            return type(self.clf)

    class SklearnWrapper_cv(object):
        def scorer(self, estimator, X, y):
            predict_arr = estimator.predict(X)
            y_arr = y
            result = (np.abs(1 - np.exp(predict_arr - y_arr))).sum() / len(y)
            return result

        def __init__(self, clf, seed=0, params=None):
            # params['random_state'] = seed
            model = clf()
            self.clf = GridSearchCV(estimator=model, param_grid=params, refit=True, scoring=self.scorer)

        def train(self, x_train, y_train):
            # print x_train
            self.clf.fit(x_train, y_train)

        def predict(self, x):
            return self.clf.predict(x)

        def clf_type(self):
            return type(self.clf)

    class XgbWrapper(object):
        def __init__(self, seed=0, params=None):
            self.param = params
            self.param["seed"] = seed
            self.nrounds = params.pop("nrounds", 250)

        def train(self, x_train, y_train):
            dtrain = xgb.DMatrix(x_train, label=y_train)
            self.gbdt = xgb.train(self.param, dtrain, self.nrounds)

        def predict(self, x):
            return self.gbdt.predict(xgb.DMatrix(x))

        def clf_type(self):
            return None

    class XgbWrapper_cv(object):
        def __init__(self, seed=0, params=None):
            # self.param = params
            # self.param["seed"] = seed
            # self.nrounds = params.pop("nrounds", 250)
            gbdt = XGBRegressor()
            self.model = GridSearchCV(gbdt, params, refit=True)

        def train(self, x_train, y_train):
            #dtrain = xgb.DMatrix(x_train, label=y_train)
            self.model.fit(x_train, y_train)

        def predict(self, x):
            return self.model.predict(x)
            #return self.model.predict(xgb.DMatrix(x))

        def clf_type(self):
            return None

    def get_oof(clf):
        oof_train = np.zeros((ntrain,))
        oof_test = np.zeros((ntest,))
        oof_test_skf = np.empty((NFOLDS, ntest))

        for i, (train_index, test_index) in enumerate(kf):
            x_tr = x_train[train_index]
            y_tr = y_train[train_index]
            x_te = x_train[test_index]

            if clf.clf_type() and clf.clf_type() == Mean_Model:
                oof_train = clf.predict(train.copy())
                oof_test_skf[i, :] = clf.predict(test.copy())
            else:
                clf.train(x_tr, y_tr)

                oof_train[test_index] = clf.predict(x_te)
                oof_test_skf[i, :] = clf.predict(x_test)

        oof_test[:] = oof_test_skf.mean(axis=0)
        # print oof_train
        # print oof_test
        return oof_train.reshape(-1, 1), oof_test.reshape(-1, 1)

    model_name = ["GB", "RF", "XGB", "XGB2", "ADA", "ET"]
    model_lst = [GradientBoostingRegressor, RandomForestRegressor, XGBRegressor, XGBRegressor,
                  AdaBoostRegressor, ExtraTreesRegressor]
    # model_params = [gbdt_params, rf_params, xgb_params, xgb_params2, ada_param, et_params]
    model_params = [gbdt_params_cv, rf_params_cv, xgb_params_cv, xgb_params2_cv, ada_param_cv, et_params_cv]
    model2_name = ["GB", "ADA", "XGB", "XGB2"]
    model2_lst = [GradientBoostingRegressor, AdaBoostRegressor, XGBRegressor, XGBRegressor]
    model2_params = [gbdt_params, ada_param, xgb_params, xgb_params2]
    model_used_idx = [[0, 1, 2],
                       [0, 1, 2, 3],
                       [0, 1, 2, 3, 4],
                       [0, 1, 2, 3, 4, 5],
                       [1, 2, 3, 4, 5],
                       [2, 3, 4, 5],
                       [3, 4, 5]]

    y_test = np.zeros((ntest,))
    for i in range(len(model_used_idx)):

        def generate_wrapper(index, names, models, params, cv=True):
            # print names[index]
            if names[index] == "XGB" or names[index] == "XGB2":
                if cv:
                    return XgbWrapper_cv(seed=SEED, params=params[index])
                else:
                    return XgbWrapper(seed=SEED, params=params[index])
            else:
                if cv:
                    return SklearnWrapper_cv(clf=models[index], seed=SEED, params=params[index])
                else:
                    return SklearnWrapper(clf=models[index], seed=SEED, params=params[index])

        # model_used = [model_lst[idx] for idx in model_used_idx[i]]
        # arams_used = [model_params[idx] for idx in model_used_idx[i]]
        wrapper_lst = [generate_wrapper(idx, model_name, model_lst, model_params)
                       for idx in range(len(model_used_idx[i]))]
        train_test_lst = [get_oof(wrapper) for wrapper in wrapper_lst]
        train_lst = [train_temp for train_temp, test_temp in train_test_lst]
        test_lst = [test_temp for train_temp, test_temp in train_test_lst]

        def scorer(data_lst1, data_lst2):
            # print data_lst1
            # print data_lst2
            return (np.abs(1 - np.exp(data_lst1.values - data_lst2.reshape((1, -1))[0]))).mean()

        for j in range(len(train_lst)):
            score = scorer(y_train, train_lst[j])
            print model_name[j] + "-CV".format(score)
            if model_name[j] in model_score_dic:
                model_score_dic[model_name[j]][0] += score
                model_score_dic[model_name[j]][1] += 1
            else:
                model_score_dic[model_name[j]] = [score, 1]
        x_train = np.concatenate(train_lst, axis=1)
        x_test = np.concatenate(test_lst, axis=1)

        print("{},{}".format(x_train.shape, x_test.shape))

        random_index = random.randint(0, 3)
        print "second floor use : " + model2_name[random_index]
        model2 = generate_wrapper(random_index, model2_name, model2_lst, model2_params, cv=False)
        model2.train(x_train, y_train)
        y_test += model2.predict(x_test)
    return y_test, len(model_used_idx), test_index, test_tollgate, test_direction


def main():
    result_df = pd.DataFrame()
    print u"训练集用train&test的数据，非调参另一种Stacking模型，训练集用单模型结果为0.1647的特征"

    print "NFOLD = " + str(NFOLDS)
    for tollgate_id, direction, offset, time_period in tuple_lst:
        print tollgate_id
        print direction
        print offset
        y_test1, length1, test_index = predict1(tollgate_id, direction, offset, time_period)
        # y_test2, _, _ = predict2(tollgate_id, direction, offset)
        # y_test = (y_test1 + y_test2) / (length1 + length2)
        y_test = y_test1 / length1
        # y_test, test_index = predict0(tollgate_id, direction, offset)

        y_predict = pd.DataFrame()
        y_predict["volume_float"] = np.exp(y_test)
        y_predict.index = test_index
        y_predict["tollgate_id"] = tollgate_id
        y_predict["time_window"] = y_predict.index
        y_predict["time_window"] = y_predict["time_window"].apply(lambda time_basic: "[" + str(pd.Timestamp(time_basic) + DateOffset(minutes=(6 + offset) * 20)) + "," + str(
                    pd.Timestamp(time_basic) + DateOffset(minutes=((6 + offset) + 1) * 20)) + ")")
        y_predict["direction"] = direction
        y_predict["volume"] = y_predict["volume_float"].apply(lambda x: "%.2f" % x)
        del y_predict["volume_float"]
        result_df = result_df.append(y_predict)

    #result2_df = pd.DataFrame()
    #for offset in range(6):
    #    y_test1, len1, test_index, test_tollgate, test_direction = predict3(offset)
    #    y_test = y_test1 / len1
    #    y_predict = pd.DataFrame()
    #    y_predict["volume_float"] = np.exp(y_test)
    #    y_predict.index = test_index
    #    y_predict["tollgate_id"] = test_tollgate
    #    y_predict["time_window"] = y_predict.index
    #    y_predict["time_window"] = y_predict["time_window"].apply(
    #        lambda time_basic: "[" + str(pd.Timestamp(time_basic) + DateOffset(minutes=(6 + offset) * 20)) + "," + str(
    #            pd.Timestamp(time_basic) + DateOffset(minutes=((6 + offset) + 1) * 20)) + ")")
    #    y_predict["direction"] = test_direction
    #    y_predict["volume"] = y_predict["volume_float"].apply(lambda x: "%.2f" % x)
    #    del y_predict["volume_float"]
    #    result2_df = result2_df.append(y_predict)

    try:
        for i in range(len(model_used_name)):
            name = model_used_name[i]
            if name in model_score_dic:
                score = model_score_dic[name][0] / model_score_dic[name][1]
                print name + "-stacking : %.5f" % (score,)
        print result_df.sort_values(["tollgate_id", "direction"])
    except Exception as e:
        print e

    result_df["tollgate_id"] = result_df["tollgate_id"].replace({"1S": 1, "2S": 2, "3S": 3})
    result_df["direction"] = result_df["direction"].replace({"entry": 0, "exit": 1})
    output_file = "./train&test1_zjw/volume_predict_stacking_pure.csv"
    result_df.to_csv(output_file, index=None, encoding="utf8")
    print output_file

main()
