import tensorflow as tf
from tensorflow.keras import layers, losses
from tensorflow.keras.models import Model

from sklearn.model_selection import train_test_split


# https://www.tensorflow.org/tutorials/generative/autoencoder
class ADAutoencoder(Model):
    def __init__(self, size, stddev, dropout, hidden):
        super(ADAutoencoder, self).__init__()
        self.encoder = tf.keras.Sequential([
            layers.Input(shape=(size,)),
            layers.GaussianNoise(stddev=stddev),
            layers.Dense(size * hidden, activation="relu")])
        self.decoder = tf.keras.Sequential([
            layers.Dropout(dropout),
            layers.Dense(size, activation='sigmoid')])
        # layers.Softmax(input_dim=size, axis=-1)

    def call(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded
