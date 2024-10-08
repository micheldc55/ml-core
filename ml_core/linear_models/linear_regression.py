import numpy as np
from numpy.typing import ArrayLike

from ml_core.core_components.model import RegressionModel
from ml_core.core_components.linalg import is_invertible_svd


class LinearRegression(RegressionModel):
    """Linear regression model."""
    def __init__(self, compute_stats: bool = False):
        super().__init__(name="LinearRegression")
        self.coef_ = None
        self.intercept_ = None
        self.betas_ = None
        self.degrees_of_freedom = None
        self.num_predictors = None
        self.trained = False
        self.compute_stats = compute_stats

    def fit(self, X: ArrayLike, y: ArrayLike):
        """Fit the model to the data.
        
        Args:
            X (ArrayLike): The input data.
            y (ArrayLike): The target data.
        """
        X = self._preprocess_input_matrix(X)
        y = self._preprocess_input_vector(y)

        self.x_ = X
        self.y_ = y

        self._check_degrees_of_freedom(X.shape[0] - X.shape[1])
        self.degrees_of_freedom = X.shape[0] - X.shape[1]
        self.num_predictors = X.shape[1] - 1

        self._check_is_matrix_invertible(X.T @ X)

        self.betas_ = np.linalg.inv(X.T @ X) @ X.T @ y
        self.intercept_ = self.betas_[0]
        self.coef_ = self.betas_[1:]
        self.trained = True

    def predict(self, X: ArrayLike):
        """Make predictions using the model."""
        x_array = self._preprocess_input_mat_if_needed(X)
        return x_array @ self.betas_
    
    def save(self, path: str):
        raise NotImplementedError
    
    def load(self, path: str):
        raise NotImplementedError
    
    def get_params(self):
        params_dict = {
            f"beta_x_{i + 1}": coef
            for i, coef in enumerate(self.coef_)
        }
        params_dict["intercept"] = self.intercept_
        return params_dict
    
    def compute_t_statistics(self) -> ArrayLike:
        """Compute the t-statistics of the model."""
        standard_errors = self.compute_standard_errors()
        return self.betas_ / standard_errors
    
    def compute_f_statistic(self) -> float:
        """Compute the F-statistic of the model."""
        y_pred = self.predict(self.x_)
        sst = self._compute_total_sum_squares(self.y_)
        ssr = self._compute_sum_squared_residuals(y_pred, self.y_)
        return (sst - ssr) * self.degrees_of_freedom / (self.num_predictors * ssr)
    

    def get_residuals(self) -> ArrayLike:
        """Get the residuals of the model."""
        y_true_vec = self._preprocess_input_vector(self.y_)
        return y_true_vec - self.predict(self.x_)
    

    def get_residuals_summary_stats(self) -> dict:
        """Get summary statistics of the residuals."""
        residuals = self.get_residuals()
        return {
            "min": np.min(residuals),
            "1Q": np.percentile(residuals, 25),
            "median": np.median(residuals),
            "3Q": np.percentile(residuals, 75),
            "max": np.max(residuals)
        }
    

    def compute_standard_errors(self) -> ArrayLike:
        """Compute the standard errors of the model."""
        covariance_matrix = self._compute_covariance_matrix()
        return np.sqrt(np.diag(covariance_matrix))
    

    def compute_r_squared(self) -> float:
        """Compute the R-squared of the model."""
        y_pred = self.predict(self.x_)
        sst = self._compute_total_sum_squares(self.y_)
        ssr = self._compute_sum_squared_residuals(y_pred, self.y_)
        return 1 - ssr / sst
    

    def compute_adjusted_r_squared(self) -> float:
        """Compute the adjusted R-squared of the model."""
        r_squared = self.compute_r_squared()

        return 1 - (1 - r_squared) * self.num_predictors / self.degrees_of_freedom
    

    def get_residual_standard_error(self) -> float:
        """Get the residual standard error of the model."""
        return np.std(self.get_residuals())
    

    @staticmethod
    def _check_is_matrix_invertible(X: ArrayLike):
        """Checks if a matrix (X) is invertible."""
        if not is_invertible_svd(X):
            raise ValueError(f"Matrix is not invertible.")
        

    @staticmethod
    def _include_intercept_column(X: ArrayLike):
        """Include an intercept column in the matrix. Adds a column 
        of ones to the matrix X to account for beta_0."""
        return np.hstack([np.ones((X.shape[0], 1)), X])
    

    @staticmethod
    def _check_degrees_of_freedom(degrees_of_freedom: int):
        """Check if the degrees of freedom are valid."""
        if degrees_of_freedom <= 0:
            raise ValueError("Degrees of freedom must be greater than 0.")
    

    def _preprocess_input_matrix(self, X: ArrayLike) -> ArrayLike:
        """Preprocess the input matrix."""
        x_copy = X.copy()
        x_copy = np.array(x_copy)

        if x_copy.ndim == 1:
            x_copy = x_copy.reshape(-1, 1)

        return self._include_intercept_column(x_copy)
    

    def _check_preprocess_is_needed(self, X: ArrayLike) -> bool:
        """Check if the input matrix needs to be preprocessed."""
        beta_len = len(self.betas_) if self.betas_ is not None else 0
        if X.shape[1] != beta_len:
            return True
        return False
    

    def _preprocess_input_mat_if_needed(self, X: ArrayLike) -> ArrayLike:
        """Preprocess the input matrix if needed."""
        if self._check_preprocess_is_needed(X):
            return self._preprocess_input_matrix(X)
        return X
    

    def _preprocess_input_vector(self, y: ArrayLike) -> ArrayLike:
        """Preprocess the input vector."""
        return np.array(y).copy()

    
    def _get_residuals_variance(self) -> float:
        """Get the variance of the residuals."""
        residuals = self.get_residuals()
        return np.sum(np.square(residuals)) / self.degrees_of_freedom
    

    def _compute_covariance_matrix(self) -> ArrayLike:
        """Compute the covariance matrix of the model."""
        residuals_variance = self._get_residuals_variance()
        return residuals_variance * np.linalg.inv(self.x_.T @ self.x_)
    

    def _compute_total_sum_squares(self, y_true: ArrayLike) -> float:
        """Compute the total sum of squares of the mean as a (naive) predictor. 
        Also known as SST (sum of squares total)."""
        y_vec = self._preprocess_input_vector(y_true)
        return np.sum(np.square(y_vec - np.mean(y_vec)))
    

    def _compute_sum_squares_regression(self, y_pred: ArrayLike, y_true: ArrayLike) -> float:
        """Compute the sum of squares regression. This is the sum of squared 
        errors made by the model."""
        return np.sum(np.square(y_pred - np.mean(y_true)))
    

    def _compute_sum_squared_residuals(self, y_pred: ArrayLike, y_true: ArrayLike) -> float:
        """Compute the sum of squared residuals."""
        return np.sum(np.square(y_true - y_pred))
    

    def __repr__(self):
        return "\n".join([f"beta_{i}: {beta}" for i, beta in enumerate(self.betas_)])


    def __str__(self):
        return self.__repr__()