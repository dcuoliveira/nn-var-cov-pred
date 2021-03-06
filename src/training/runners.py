import os
import pandas as pd
from tqdm import tqdm
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from training import optimization as opt
from utils import Pyutils as pyutils

def run_model_training(target_name,
                       inputs_path,
                       outputs_path,
                       dataset_names,
                       model_tag,
                       standardize,
                       train_size,
                       wrapper,
                       n_jobs,
                       n_splits,
                       n_iter,
                       seed,
                       verbose,
                       output_ovrd):

    for dir_name in tqdm(os.listdir(inputs_path),
                         desc="Running " + model_tag + " model for all DGPs"):
        for d_name in dataset_names:

            if output_ovrd:
                check_pickle = os.path.exists(os.path.join(outputs_path, model_tag, dir_name, d_name + "_model.pickle"))
                check_pred = os.path.join(outputs_path, model_tag, dir_name, d_name + "_result.csv")
                if check_pickle and check_pred:
                    continue

            train_data = pd.read_csv(os.path.join(inputs_path, dir_name, d_name + ".csv"))
            train_data.set_index(["Var1", "Var2"], inplace=True)
            y_train = train_data[[target_name]].to_numpy()
            X_train = train_data.drop([target_name], axis=1).to_numpy()

            test_data = pd.read_csv(os.path.join(inputs_path, dir_name, d_name + "_test.csv"))
            test_data.set_index(["Var1", "Var2"], inplace=True)
            y_test = test_data[[target_name]].to_numpy()
            X_test = test_data.drop([target_name], axis=1).to_numpy()

            if standardize:
                X_train, X_validation, y_train, y_validation = train_test_split(X_train, y_train, train_size=train_size)

                scaler = StandardScaler()
                X_train_zscore = scaler.fit_transform(X_train)
                X_validation_zscore = scaler.transform(X_validation)
                X_test_zscore = scaler.transform(X_test)

            if model_tag == "ffnn":
                ModelWrapper = wrapper(model_params={"input_shape": [X_train.shape[1]]})
            else:
                ModelWrapper = wrapper()

            if ModelWrapper.search_type == "direct_fit":
                model_search = ModelWrapper.ModelClass.fit(X=X_train_zscore,
                                                      y=y_train)
                test_pred = model_search.predict(X_test_zscore)

            else:
                model_search = opt.hyper_params_search(X=X_train_zscore,
                                                       y=y_train,
                                                       validation_data=(X_validation_zscore, y_validation),
                                                       wrapper=ModelWrapper,
                                                       n_jobs=n_jobs,
                                                       n_splits=n_splits,
                                                       n_iter=n_iter,
                                                       seed=seed,
                                                       verbose=verbose)
                test_pred = model_search.best_estimator_.predict(X_test_zscore)

            output = pd.DataFrame({"Var1": test_data.reset_index()["Var1"],
                                   "Var2": test_data.reset_index()["Var2"],
                                   "y": y_test.ravel(),
                                   "pred": test_pred.ravel()})
            model_output = {"model_search": model_search}

            # Check dir 1
            if not os.path.isdir(os.path.join(outputs_path, model_tag)):
                os.mkdir(os.path.join(outputs_path, model_tag))

            # Check dir 2
            if not os.path.isdir(os.path.join(outputs_path, model_tag, dir_name)):
                os.mkdir(os.path.join(outputs_path, model_tag, dir_name))

            output.to_csv(os.path.join(outputs_path, model_tag, dir_name, d_name + "_result.csv"), index=False)
            pyutils.save_pkl(data=model_search.best_params_,
                             path=os.path.join(outputs_path, model_tag, dir_name, d_name + "_model.pickle"))