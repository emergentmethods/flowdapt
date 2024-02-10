# Building a pipeline with DataSieve

Flowdapt allows you to build any pipeline that may suit your needs with which ever tools let you do that in Python. However, many of the example plug-ins make use of a library called [`DataSieve`](https://github.com/emergentmethods/datasieve). DataSieve is very similar to the SKlearn Pipeline in that it:

- fits an arbitrary series of transformations to an array X
- transforms subsequent arrays of the same dimension according to the fit from the original X
- inverse transforms arrays by inverting the series of transformations

This means that it follows the SKLearn API very closely, and in fact users can use SKLearn transforms directly without making any modifications.

The main **difference** is that DataSieve allows for the manipulation of the y and sample_weight arrays in addition to the X array. This is useful if you find yourself wishing to use the SKLearn pipeline for:

- removing outliers across your X, y, and sample_weights arrays according to simple or complex criteria
- remove feature columns based on arbitrary criteria (e.g. low variance features)
- change feature column names at certain transformations (e.g. PCA)
- needing outlier classification without removal (see `oulier_check`)
- passing dynamic parameters to individual transforms of the pipeline
- passing dataframes/arrays without worrying about converting to arrays and maintaining the proper feature columns
- customizing backend for parallelization (e.g. Dask, Ray, loky, etc.)

These improved flexibilities allow for more customized/creative transformations. For example, the included `DBSCAN` has automated parameter fitting and outlier removal based on clustering. 


## Usage
The user builds the pipeline similarly to SKLearn, and can even use SKLearn transforms directly with the `SKLearnWrapper`:

```python
    from datasieve.pipeline import Pipeline
    import datasieve.transforms as dst
    from sklearn.preprocessing import MinMaxScaler

    feature_pipeline = Pipeline([
        ("detect_constants", dst.VarianceThreshold(threshold=0)),
        ("pre_svm_scaler", dst.SKlearnWrapper(MinMaxScaler(feature_range=(-1, 1)))),
        ("svm", dst.SVMOutlierExtractor()),
        ("pca", dst.PCA(n_components=0.95)),
        ("post_pca_scaler", dst.SKlearnWrapper(MinMaxScaler(feature_range=(-1, 1))))
    ])

```

Once the pipeline is built, it can be fit and transformed similar to a SKLearn pipeline:

```python
X, y, sample_weight = feature_pipeline.fit_transform(X, y, sample_weight)
```

This pipeline demonstrates the various components of `DataSieve` which are missing from SKLearn's pipeline. A dataframe `X` (if desired, else users can input a numpy array without column names) is input with its associated `y` and `sample_weight` arrays/vectors (these are also optional). The `VarianceThreshold` will first detect and remove any features that have zero variance in X, the `SVMOutlierExtractor` will fit `SGDOneClassSVM` to `X` and then remove the detected outliers in `X`, while also propagating those row removals from `y` and `sample_weight`. Finally, the `PCA` will be fit to the remaining `X` array with the features count changing and getting renamed. The returned `X` dataframe will have the correctly named column features/count, and equal row counts across the `X`, `y`, and `sample_weight` arrays.

Next, the `feature_pipeline` can then be used to transform other datasets with the same input feature dimension:

```python
Xprime, _, _ = feature_pipeline.transform(X2)
```

Finally, similar to SKLearn's pipeline, the `feature_pipeline` can be used to inverse_transform the array `Xprime` array that has the same dimensions as the returned `X2`/`X` array from the pipeline:

```python
X2, _ ,_ = feature_pipeline.inverse_transform(Xprime)
```


## Creating a custom transform

An example would be someone who wants to use `SGDOneClassSVM` to detect and remove outliers from their data set before training:

```python
class SVMOutlierExtractor(BaseTransform):
    """
    A subclass of the SKLearn SGDOneClassSVM that adds a transform() method
    for removing detected outliers from X (as well as the associated y and
    sample_weight if they are also furnished.
    """

    def __init__(self, **kwargs):
        self._skl = SGDOneClassSVM(**kwargs)

    def fit_transform(self, X, y=None, sample_weight=None, feature_list=None, **kwargs):
        self.fit(X, y, sample_weight=sample_weight)
        return self.transform(X, y, sample_weight, feature_list)

    def fit(self, X, y=None, sample_weight=None, feature_list=None, **kwargs):
        self._skl.fit(X, y=y, sample_weight=sample_weight)
        return X, y, sample_weight, feature_list

    def transform(self, X, y=None, sample_weight=None, feature_list=None,
                  outlier_check=False, **kwargs):
        y_pred = self._skl.predict(X)
        y_pred = np.where(y_pred == -1, 0, y_pred)
        if not outlier_check:
            X, y, sample_weight = remove_outliers(X, y, sample_weight, y_pred)
            num_tossed = len(y_pred) - len(X)
            if num_tossed > 0:
                logger.info(
                    f"SVM detected {num_tossed} data points "
                    "as outliers."
                )
        else:
            y += y_pred
            y -= 1

        return X, y, sample_weight, feature_list

    def inverse_transform(self, X, y=None, sample_weight=None, feature_list=None, **kwargs):
        """
        Unused
        """
        return X, y, sample_weight, feature_list
```


As shown here, the `fit()` method is actually identical to the SKLearn `fit()` method, but the `transform()` removes data points from X, y, and sample_weight for any outliers detected in the `X` array.

## Data removal

The command `feature_pipeline.fit_transform(X, y, sample_weight)` fits each pipeline step to `X`, and transforms `X` according to each step's `transform()` method. In some cases, this will not affect `y` or `sample_weight`. For example, `MinMaxScaler` simply scales `X` and saves the normalization information.  Meanwhile, in the `SVMOutlierExtractor`, `.fit()` will fit an SVM to `X` and `.transform()` will remove any detected outliers from `X`. Typical `Scikit-Learn` pipelines do not remove those data points from `y` and `sample_weight`. Luckily, the `Pipeline` takes care of the "associated removal" of the same outlier data points from `y` and `sample_weight`. 

## Feature modification

Another feature is demonstrated in the `PCA`, which fits a PCA transform to `X` and then transforms `X` to principal components. This dimensionality reduction means that the features are no longer the same, instead they are now `PC1`, `PC2` ... `PCX`. `Pipeline` handles the feature renaming at that step (which is not a feature available in the `Scikit-Learn` pipeline). Similar to `FlowdaptPCA`, the `VarianceThreshold` subclasses the `Scikit-Learn` `VarianceThreshold` which is geared toward removing features that have a low variance. `VarianceThreshold` ensures that the removed features are properly handled when `X` passes through this part of the pipeline.

## Adding a custom step

Each step of the `Pipeline` *must* contain the following methods:

```python
class MyTransformer(BaseTransform):
    def fit_transform(self, X, y=None, sample_weight=None, feature_list=None, **kwargs):
        """
        This method is defined by default by the BaseTransform class. But users can override
        to do something unique (see DBSCAN where this is particularly useful.)
        """
        X, y, sample_weight = self.fit(X, y, sample_weight)
        return self.transform(X, y, sample_weight)

    def fit(self, X, y=None, sample_weight=None, feature_list=None, **kwargs):
        """
        Some fun fitting method
        """
        return X, y, sample_weight, feature_list

    def transform(self, X, y=None, sample_weight=None, feature_list=None, **kwargs):
        """
        Transformation of X or y or sample_weight or all three, anything the user
        wants.
        """
        return X, y, sample_weight, feature_list

    def inverse_transform(self, X, y=None, sample_weight=None, feature_list=None, **kwargs):
        """
        The inverse transform - it is defined like this by default in BaseTransform class
        """
        return X, y, sample_weight, feature_list
```

This is because these four methods are called automatically by the `Pipeline` object. In most cases, the goal is to add functionality for an existing transformer from the `Scikit-Learn` library. Here is an example of subclassing the `MinMaxScaler` to work with the `FlowdaptPipeline`:

```python
class DataSieveMinMaxScaler(MinMaxScaler):
    """
    A subclass of the SKLearn MinMaxScaler that ensures fit, transform, fit_transform and
    inverse_transform all take the full set of params X, y, sample_weight (even if they
    are unused) to follow the FlowdaptPipeline API.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def fit_transform(self, X, y=None, sample_weight=None, feature_list=None, **kwargs):
        super().fit(X)
        X = super().transform(X)
        return X, y, sample_weight, feature_list

    def fit(self, X, y=None, sample_weight=None, feature_list=None, **kwargs):
        super().fit(X)
        return X, y, sample_weight, feature_list

    def transform(self, X, y=None, sample_weight=None, feature_list=None, **kwargs):
        X = super().transform(X)
        return X, y, sample_weight, feature_list

    def inverse_transform(self, X, y=None, sample_weight=None, feature_list=None, **kwargs):
        return super().inverse_transform(X), y, sample_weight, feature_list
```


## Outlier checking

DataSieve also allows users to fit a pipeline that can be used to flag outliers in data *without* removing them from the dataset. This may be handy in a variety of cases where keeping the data point is important but having some indication of which points are outliers is also important. In order to use this functionality, you can take an already `fit` pipeline and call `transform(X, outlier_check=True)` which will return X as well as a vector of 1s and 0s indicating which points are outliers. This is demonstrated in the following example:

```python
pipeline = Pipeline([
    ("pre_svm_scaler", transforms.DataSieveMinMaxScaler()),
    ("svm", transforms.SVMOutlierExtractor())
])

pipeline.fit(X)

X, outliers, _ = pipeline.transform(X, outlier_check=True)
```

Now X will *not* have any of the outlier data points removed, but the vector `outliers` will be an indication of which points were classified as outliers, where 0 means the point was an outlier and 1 means that the point was an inlier.


# Installation

The easiest way to install `datasieve` is with:

```
pip install datasieve
```

but you can also clone this repository and install it with:

```
git clone https://github.com/emergentmethods/datasieve.git
cd datasieve
poetry install
```
