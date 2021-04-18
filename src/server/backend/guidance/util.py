import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import mean_squared_error


# https://stackoverflow.com/questions/27928275/find-p-value-significance-in-scikit-learn-linearregression
def compute_regression_statistics(classifier, data, descriptive_features, target_feature):
    # Load linear regression coefficients
    params = np.append(classifier.intercept_, classifier.coef_)
    predictions = classifier.predict(data[descriptive_features])
    mean_se = mean_squared_error(data[target_feature], predictions)
    try:
        # Load original descriptive features
        data = data[descriptive_features]

        # Append column of ones to descriptive features dataframe for matrix calculation of linear regression
        data_w_constant = np.append(np.ones((len(data), 1)), data, axis=1)

        # Estimate the variances of each descriptive feature in the linear regression model (incl. the intercept)
        var_b = mean_se * (np.linalg.inv(np.dot(data_w_constant.T, data_w_constant)).diagonal())

        # If a variance is estimated to be negative, correct for this anomaly
        if np.any(var_b < 0):
            print('The above estimates for the variance are negative. This is impossible for the actual variance' +
                  ', so we set it to zero.')
            var_b = var_b.clip(min=0)

        # Calculate standard errors on basis of variances
        sd_b = np.sqrt(var_b)

        # Calculate t-values for each coefficient
        ts_b = params / sd_b

        # Calculate the p-values for each coefficient
        p_values = [2 * (1 - stats.t.cdf(np.abs(i), (len(data_w_constant) - 1))) for i in ts_b]

        # Round to the third decimal place for display
        sd_b = np.round(sd_b, 3)
        ts_b = np.round(ts_b, 3)
        p_values = np.round(p_values, 3)
        params = np.round(params, 4)

        # Create dataframe containing all statistics for display
        df = pd.DataFrame()
        descriptions = ['Constant'] + list(data.columns)
        df["Descriptive feature"] = descriptions
        df["Coefficients"] = params
        df["Standard Errors"] = sd_b
        df["t values"] = ts_b
        df["p values"] = p_values
        return df

    # Catch possible linear algebra errors in the case a matrix is singular
    except np.linalg.LinAlgError as err:
        if 'Singular matrix' in str(err):
            print('Impossible to calculate standard errors, t values and p values, as the '
                  + 'matrix of the constant and descriptive features is singular')
        else:
            raise