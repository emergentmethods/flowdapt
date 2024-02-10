# Tensorboard

`FlowML` provides a Tensorboard logger that tracks PyTorch/XGBoost model training loss and validation loss by default. These logs are saved with the workflow artifacts directory. If you are running locally, then this would be on the local disk. If you are running on distributed storage, then the logs are saved accordingly.

```
tensorboard --logdir path/to/artifacts/<study_identifier>/
```

where the `study_identifier` is the value passed into the configuration file. This will start a local server, which is typically accessed at `127.0.0.1:6006` in a browser.

## Adding custom metrics

`FlowML` models allow users to use the tensorboard logger by default by simply adding the following lines to their training loop:

```python

# Train loop here:
for epoch in epochs:
    for batch in batches:
        x, y_target = batch
        y_pred = model(x)
        loss = criterion(y_pred, y_target)
        # Backprogation
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        train_loss += loss.item()

    self.log("train_loss", train_loss, step=epoch)
```

This will start logging `train_loss` in the logger, which will become available in the artifacts directory for post-processing.

If you wish to start a new tensorboard log, you can simply call `self.reset_logger()` at the end of each training.