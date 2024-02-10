# Leveraging `flowml`

As usual, Flowdapt allows users to import and use any machine learning tools they may need to solve their unique problems. However, we designed a complimentary library called ['flowml'](https://url.com/flowdapt/flowml), which is designed to improve quality of life when working with thousands of models. The models contained in `flowml` are optimized for cluster memory/artifact handling, and they are battle tested for time-series adaptive modeling.

`flowml` is a python package built for supplying time-series forecasting models in a large scale adaptive modeling environment. In particular, flowml is built to be used with [flowdapt](https://docs.flowdapt.ai), a platform for adaptive modeling. Flowdapt has an optimized approach to cluster memory handling which is supported by all models in this library. This optimized cluster-memory approach enables rapid inferencing, quick re-training, cheap concept-drift-detection, and easy hyperparameter tuning. Currently, the library provides models for:

- LSTM direct regression (PyTorchLSTMDirect)
- LSTM Autoregressive forecasting (PyTorchLSTMAutoregressive)
- Transformer based regression (PyTorchTransformer)
- MLP regression (PyTorchMLPRegressor)
- Gradient boosted decision tree (XGBoostRegressor) regression

and the structure enables easy addition of new models or tweaking of the existing ones. 


## Installation

For normal use users can install flowml via pip (given an access token):
```bash
pip install flowml
```

## Usage

flowml can be imported from the `flowml` package and used as a normal python package:

```python
from flowml.models import PyTorchLSTMDirect

model = PyTorchLSTMDirect(
    input_features=200,
    hidden_dim=64,
    output_features=6,
    num_layers=2,
    dropout=0.2,
    batch_size=32,
    epochs=10
)
```

which will define the LSTM model. Next, it can be called with a set of training data, following the SKLearn API:

```python
x = np.random.rand(100, 200)
y = np.random.rand(100, 6)
model.fit(x, y)
```

the fitted model can then be used to make inferences on new data:

```python
x = np.random.rand(10, 200)
y_hat = model.predict(x)
```

## Usage with cluster memory and distributed storage

flowml models are optimized to be stored on distributed storage or in Flowdapt's cluster memory. Typically this is as simple as:

```python
from flowdapt.compute import object_store

object_store.put("model_name", model)
model = object_store.get("model_name")
```

which would allow a model to be quickly accessed from anywhere in a Flowdapt cluster. The model can be saved to the distributed storage using the `artifact_only` argument:

```python
object_store.put("model_name", model, artifact_only=True)
model = object_store.get("model_name", artifact_only=True)
```

## Usage with the PipeFill

The PipeFill object is designed to easily contain, move, and organize models in the Flowdapt cluster. The need arises when thousands of heterogeneous models need to be trained, inferenced, stored, and tuned. In many cases, each model has its own unique data processing methods (e.g. scaling, outlier detection, dimensionality reduction [details here](pipeline.md)). Many of these data processing methods require auxillary data such as the training data itself and trained models (e.g. SVM).

The flowml `PipeFill` object is designed to organize all these auxillary objects, persist them to disk, and ensure they are properly coordinated between training and inferencing. The `PipeFill` also has helper functions for quickly creating/storing train/test data.

Typically, a train stage would instantiate the `PipeFill` object and start building and attaching objects to it. For example, we use helper function `make_pipe_fill` to create a `PipeFill` object:

```python
from flowml.pipefill import PipeFill
from datasieve.pipeline import Pipeline
import datasieve.transforms as ds
from flowdapt.compute import object_store
from sklearn.preprocessing import MinMaxScaler

def train_stage(*args):

    # create the PipeFill object which instantiates the flowml.XGBoostRegressor
    # automatically internally
    pf = PipeFill(
        name_str="descriptive_pipefill_name",
        study_identifier="namespace",
        model_str="flowml.models.XGBoostRegressor",
        model_train_params=model_train_parameters,
        data_split_params=data_split_parameters,  
        extras=extras
    )

    X = np.random.rand(100, 200)
    y = np.random.rand(100, 6)

    # helper function to automatically split the train and test datasets inside the
    # pipefill and create the eval_set
    X, y, w, Xt, yt, wt = mlutils.make_train_test_datasets()

    # make the data preprocessing pipeline dict containing all the params that the user
    # wants to pass to each step. They can miss them if they dont want to pass values
    # (use defaults)
    fitparams: dict[str, dict] = {"raw_scaler": {}}
    pf.feature_pipeline = Pipeline([
        ("raw_scaler", ds.SKLearnWrapper(MinMaxScaler())),
        ("detect_constants", ds.VarianceThreshold(threshold=0)),
    ],
        fitparams)

    # fit the feature pipeline to the features and transform them in one call
    X, y, w = pf.feature_pipeline.fit_transform(X, y, w)
    # transform the test set using the fitted pipeline
    Xt, yt, wt = pf.feature_pipeline.transform(Xt, yt, wt)

    # the labels require a separate pipeline (the objects are fit in a the label parameter
    # space.)
    pf.target_pipeline = Pipeline([
        ("scaler", ds.SKLearnWrapper(MinMaxScaler()))
    ], fitparams)

    y, _, _ = pf.target_pipeline.fit_transform(y)
    yt, _, _ = pf.target_pipeline.transform(yt)

    eval_set = pf.make_eval_set()

    pf.model.fit(X, y, eval_set=eval_set)

    pf.set_trained_timestamp()

    object_store.put(pf.name_str, pf)

    return
```

???+ note "Note"
    Here we use the DataSieve `Pipeline` object, but details can be found [here](https://github.com/emergentmethods/datasieve).

We see how the `feature_pipeline` and `target_pipeline` are both fit and attached to the `pf` object. The `PipeFill` object is then saved to disk with helper function `save_pipefill()`. This object is now sitting on the disk, ready to be loaded when any other stage/workflow may need it. For example, an inferencing stage would load the `PipeFill`:

```python
from flowdapt.compute import object_store
def inference_stage(*args):

    # look for the pipefill in the cluster memory
    pf = object_store.get("descriptive_pipefill_name")

    x = np.random.rand(10, 200)

    # use the pipeline that was fit in train_stage to transform the features
    pf.pred_features, _, _ = pf.feature_pipeline.transform(x)

    preds = pf.model.predict(pf.pred_features)

    # inverse transform the targets using the fit pipeline
    preds, _, _ = pf.target_pipeline.inverse_transform(preds.reshape(-1, 1))

    return preds
```

