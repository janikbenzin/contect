from math import ceil

import tensorflow as tf
from itertools import islice

from contect.available.available import AvailableDetectors
from contect.deviationdetection.detectors.autoencoder.objects.autoencoder import ADAutoencoder
from contect.deviationdetection.detectors.autoencoder.param.config import AutoencParameters
from contect.deviationdetection.util.util import classify_trace, assign_trace_classification_to_log
from contect.parsedata.objects.oclog import ObjectCentricLog, TraceAutoenc
import contect.deviationdetection.detectors.autoencoder.util as util


class AutoencDetector:
    param: AutoencParameters

    def __init__(self, param: AutoencParameters):
        self.param = param

    def detect(self, log: ObjectCentricLog) -> float:
        detector = AvailableDetectors.AUTOENC
        log_size = len(log.traces)
        n_deviating = ceil(log_size * self.param.deviating_perc)

        # Transform log into split numpy arrays
        all_data, train_data, test_data = util.transform_input(log,
                                                               list(self.param.acts),
                                                               list(self.param.ress),
                                                               self.param.vmap_params,
                                                               self.param.test_size,
                                                               self.param.max_trace_len)

        # Instantiate and train autoencoder
        autoencoder = ADAutoencoder(size=len(all_data[0]),
                                    stddev=self.param.noise,
                                    dropout=self.param.dropout,
                                    hidden=self.param.hidden)
        autoencoder.compile(optimizer=self.param.optimizer,
                            loss=self.param.loss)

        history = autoencoder.fit(all_data, all_data,
                                  epochs=self.param.epochs,
                                  batch_size=self.param.batch_size,
                                  validation_data=(test_data, test_data),
                                  shuffle=True)

        # Predict the trace using autoencoder
        reconstructions = autoencoder.predict(all_data)
        losses = tf.keras.losses.mae(reconstructions, all_data).numpy()
        results = list(zip(list(reconstructions), list(losses)))

        # Look for highest deviating perc loss -> deviating traces
        indexed_loss = dict(enumerate(results))
        sorted_loss = dict(sorted(indexed_loss.items(), key=lambda item: item[1][1], reverse=True))
        normal_loss = dict(islice(sorted_loss.items(), n_deviating + 1, None))

        for tid in log.traces:
            classify_trace(condition=tid in normal_loss,
                           score=sorted_loss[tid][1],
                           detector=detector,
                           log=log,
                           tid=tid)
            log.traces[tid].dev_inf[detector] = TraceAutoenc(true=list(all_data[tid]),
                                                             pred=sorted_loss[tid][0])

        assign_trace_classification_to_log(detector, log)
        # log.models[detector] = history
        return sorted_loss[n_deviating][1]
