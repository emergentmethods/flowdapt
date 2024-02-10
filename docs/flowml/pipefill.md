## Leveraging the FlowML PipeFill

As usual, Flowdapt does not require users to use any particular object if they have other tools that fit their needs. However, we have developed a complimentary library called ['flowml'](https://url.com/flowdapt/flowml), which is designed to improve quality of life when working with thousands of models. The `PipeFill` object is a core component of this library.

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

    object_store.put("descriptive_pipefill_name", pf)

    return
```

???+ note ""
    Here we use the DataSieve `Pipeline` object, but details can be found [here](https://github.com/emergentmethods/datasieve).

We see how the `feature_pipeline` and `target_pipeline` are both fit and attached to the `pf` object. The `PipeFill` object is then saved to disk/cluster memory with helper function `object_store.put("descriptive_pipefill_name", pf)`. This object is now sitting on the disk or cluster memory, ready to be loaded when any other stage/workflow may need it. For example, an inferencing stage would load the `PipeFill`:

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