import copy
import sys

import numpy as np
import tensorflow.keras.regularizers
from sklearn.model_selection import train_test_split
import tensorflow as tf

from utilities.EEGModels import EEGNet
from matplotlib import pyplot as plt
from functions_dataset import extract_indexes_segments


def CNN(input_shape):

    X_input = tf.keras.Input(input_shape)

    X = tf.keras.layers.Conv2D(filters=8, kernel_size=(3, 3), strides=(1, 1), padding='same', name='conv0', kernel_regularizer=tf.keras.regularizers.l1(0.01))(X_input)
    X = tf.keras.layers.BatchNormalization(axis=-1, name='bn0')(X)
    X = tf.keras.layers.Activation('relu')(X)
    X = tf.keras.layers.Dropout(rate=0.2)(X)

    # X = tf.keras.layers.Conv2D(filters=128, kernel_size=(3, 3), strides=(1, 1), padding='same', name='conv1')(X)
    # X = tf.keras.layers.BatchNormalization(axis=-1, name='bn1')(X)
    # X = tf.keras.layers.Activation('relu')(X)
    # X = tf.keras.layers.Dropout(rate=0.2)(X)
    #
    # X = tf.keras.layers.Conv2D(filters=256, kernel_size=(3, 3), strides=(1, 1), padding='same', name='conv2')(X)
    # X = tf.keras.layers.BatchNormalization(axis=-1, name='bn2')(X)
    # X = tf.keras.layers.Activation('relu')(X)
    # X = tf.keras.layers.Dropout(rate=0.2)(X)

    X = tf.keras.layers.MaxPool2D(pool_size=2)(X)

    X = tf.keras.layers.Flatten()(X)
    X = tf.keras.layers.Dense(2, activation='softmax', name='fc', kernel_regularizer=tf.keras.regularizers.l1(0.01))(X)

    model = tf.keras.Model(inputs=X_input, outputs=X)

    return model


def DNN_model_2labels(trained_model, to_be_removed=1):

    model = tf.keras.models.Sequential()
    for layer in trained_model.layers[:(-to_be_removed)]:
        model.add(layer)
    for layer in model.layers:
        layer.trainable = False
    model.add(tf.keras.layers.Dense(units=256, activation='relu', name='fc0',
                                    kernel_regularizer=tf.keras.regularizers.l1(0.0001)))
    model.add(tf.keras.layers.Dense(units=128, activation='relu', name='fc1',
                                    kernel_regularizer=tf.keras.regularizers.l1(0.0001)))
    model.add(tf.keras.layers.Dense(units=64, activation='relu', name='fc2',
                                    kernel_regularizer=tf.keras.regularizers.l1(0.0001)))
    model.add(tf.keras.layers.Dense(units=2, activation='sigmoid', name='fc3'))

    model.build()
    return model


def training_CNN(train_data, train_labels, scale, batch_size, num_epochs, model_path, necessary_redimension):

    train_data, val_data, train_labels, val_labels = train_test_split(train_data, train_labels, train_size=0.8)

    if scale:
        input_shape = (train_data[0].shape[0], train_data[0].shape[1], train_data[0].shape[2])
    else:
        input_shape = (train_data[0].shape[0], train_data[0].shape[1], 1)

    if necessary_redimension:
        train_data = np.expand_dims(train_data, 3)

    model = CNN(input_shape)
    model.compile(loss='categorical_crossentropy', optimizer="adam", metrics=['accuracy'])

    history = model.fit(x=train_data[:], y=train_labels[:], validation_data=(val_data, val_labels),
                        batch_size=batch_size, epochs=num_epochs, verbose=2)

    # plot_model_training(history, model_path)
    model.save('{}.h5'.format(model_path))

    return model


def training_EEGNet(train_data, train_labels, batch_size, num_epochs, model_path, necessary_redimension):
    """
    Function for the training of an EEGNet. In general, have been used categorical_crossentropy as loss function, adam
    optimizer and accuracy as metric. The trained model is then saved and loss and accuracy are plotted.

    :param train_data: training dataset (n.trials x n.channels x n.samples)
    :param train_labels: training labels ([0, 1] for right hand, [1, 0] for left hand: n.trials x 2)
    :param batch_size: batch size for training
    :param num_epochs: number of epochs for training
    :param model_path: path and model name
    :param necessary_redimension: boolean to indicate if redimension is necessary
    :return: trained model
    """

    train_data, val_data, train_labels, val_labels = train_test_split(train_data, train_labels, train_size=0.8)

    input_shape = (train_data[0].shape[0], train_data[0].shape[1])
    
    if necessary_redimension:
      train_data = np.expand_dims(train_data, 3)

    model = EEGNet(nb_classes=2, Chans=input_shape[0], Samples=input_shape[1])
    model.compile(loss='categorical_crossentropy', optimizer="adam", metrics=['accuracy'])

    history = model.fit(x=train_data[:], y=train_labels[:], validation_data=(val_data, val_labels),
                        batch_size=batch_size, epochs=num_epochs, verbose=2)

    plot_model_training(history, model_path)
    model.save('{}.h5'.format(model_path))

    return model


def plot_model_training(history, model_name):
    """
    Plot of loss and accuracy in training and validation tests during the training of a model

    :param history: history of the model training
    :param model_name: name of the model (will be name of the saved image)
    """

    # accuracy
    plt.plot(history.history['accuracy'])
    plt.plot(history.history['val_accuracy'])
    plt.title('model accuracy')
    plt.ylabel('accuracy')
    plt.xlabel('epoch')
    plt.legend(['train', 'test'], loc='upper left')
    plt.savefig('{}_accuracy.png'.format(model_name))
    plt.close()

    # loss
    plt.plot(history.history['loss'])
    plt.plot(history.history['val_loss'])
    plt.title('model loss')
    plt.ylabel('loss')
    plt.xlabel('epoch')
    plt.legend(['train', 'test'], loc='upper left')
    plt.savefig('{}_loss.png'.format(model_name))
    plt.close()


def ablation(dataset, labels, model, function_features=None, n_segments=4, n_channels=22, n_features=396, necessary_redimension=False):
    """
    Function to perform different types of ablation according to the XAI definition

    :param dataset: dataset on which evaluate the ablation (if a feature dataset must be evaluated, this dataset should
    be without feature extraction)
    :param labels: labels corresponding to the dataset
    :param model: model on which evaluate the ablation
    :param function_features: function for the feature extraction of the dataset
    :param n_segments: number of segments to be evaluated with XAI
    :param n_channels: number of channels to be evaluated with XAI
    :param n_features: number of features to be extracted from FBCSP
    :param necessary_redimension: boolean to indicate if redimension is necessary
    """

    print("Applying ablation...")
    zero_accuracies = ablation_zero_segments(dataset, labels, model, function_features, n_segments, n_features, necessary_redimension)

    interpolation_accuracies = ablation_linear_segments(dataset, labels, model, function_features, n_segments,
                                                        n_features, necessary_redimension)

    channel_accuracies = ablation_zero_channels(dataset, labels, model, function_features, n_channels, n_features, necessary_redimension)

    return zero_accuracies, interpolation_accuracies, channel_accuracies


def ablation_zero_segments(dataset, labels, model, function_features=None, n_segments=4, n_features=396, necessary_redimension=False):
    """
    Function to perform ablation setting at zero the segment of the signal under investigation

    :param dataset: dataset on which evaluate the ablation (if a feature dataset must be evaluated, this dataset should
    be without feature extraction)
    :param labels: labels corresponding to the dataset
    :param model: model on which evaluate the ablation
    :param function_features: function for the feature extraction of the dataset
    :param n_segments: number of segments to be evaluated with XAI
    :param n_features: number of features to be extracted with FBCSP
    :param necessary_redimension: boolean to indicate if redimension is necessary
    :return: each value of the array represents the accuracy obtained without the corresponding segment
    """

    # Extract the indices of each segment

    indexes = extract_indexes_segments(dataset.shape[2], n_segments)
    accuracies = np.empty(n_segments)

    for k in range(n_segments):

        data = copy.deepcopy(dataset)
        start, end = indexes[k]

        # Set at zero the segment under investigation and re-build the dataset

        data[:, :, start:end] = np.zeros((data.shape[0], data.shape[1], end - start))

        if function_features is not None:
            if function_features.__name__ == "extractFBCSP":
                x = function_features(dataset, labels, n_features)
            else:
                x = function_features(data)
        else:
            x = data

        # Evaluate difference of accuracy
        if necessary_redimension:
            x = np.expand_dims(x, 3)
        
        results = model.evaluate(x, labels, verbose=0)
        accuracies[k] = results[1]

    return accuracies


def ablation_linear_segments(dataset, labels, model, function_features=None, n_segments=4, n_features=396, necessary_redimension=False):
    """
    Function to perform ablation setting the segment under investigation with a linear function

    :param dataset: dataset on which evaluate the ablation (if a feature dataset must be evaluated, this dataset should
    be without feature extraction)
    :param labels: labels corresponding to the dataset
    :param model: model on which evaluate the ablation
    :param function_features: function for the feature extraction of the dataset
    :param n_segments: number of segments to be evaluated with XAI
    :param n_features: number of features to be extracted with FBCSP
    :param necessary_redimension: boolean to indicate if redimension is necessary
    :return: each value of the array represents the accuracy obtained without the corresponding segment
    """

    # Extract the indices of the segments

    indexes = extract_indexes_segments(dataset.shape[2], n_segments)
    accuracies = np.empty(n_segments)

    for k in range(n_segments):

        data = copy.deepcopy(dataset)
        start, end = indexes[k]

        # For each channel inside each trial, substitute the segment under investigation with a linear function (between
        # the extremities) and rebuild the dataset

        for j in range(data.shape[0]):
            for i in range(data.shape[1]):
                prev = data[j, i, start]
                cons = data[j, i, end - 1]
                lin_len = end - start

                lin = np.linspace(prev, cons, num=lin_len)
                data[j, i, start:end] = lin

        if function_features is not None:
            if function_features.__name__ == "extractFBCSP":
                x = function_features(dataset, labels, n_features)
            else:
                x = function_features(data)
        else:
            x = data

        # Evaluate the difference of accuracies
        if necessary_redimension:
            x = np.expand_dims(x, 3)
        results = model.evaluate(x, labels, verbose=0)
        accuracies[k] = results[1]

    return accuracies


def ablation_zero_channels(dataset, labels, model, function_features=None, n_channels=22, n_features=396, necessary_redimension=False):
    """
    Function to perform ablation setting the signal from the channel under investigation at zero

    :param dataset: dataset on which evaluate the ablation (if a feature dataset must be evaluated, this dataset should
    be without feature extraction)
    :param labels: labels corresponding to the dataset
    :param model: model on which evaluate the ablation
    :param function_features: function for the feature extraction of the dataset
    :param n_channels: number of channels to be evaluated with XAI
    :param n_features: number of features to be extracted with FBCSP
    :param necessary_redimension: boolean to indicate if redimension is necessary
    :return: each value of the array represents the accuracy obtained without the corresponding segment
    """

    accuracies = np.empty(n_channels)

    for k in range(n_channels):

        data = copy.deepcopy(dataset)

        # Set the channel values of zero and rebuild the dataset

        data[:, k, :] = np.zeros((data.shape[0], data.shape[2]))

        if function_features is not None:
            if function_features.__name__ == "extractFBCSP":
                x = function_features(dataset, labels, n_features)
            else:
                x = function_features(data)
        else:
            x = data

        # Evaluate the difference of accuracies
        if necessary_redimension:
          x = np.expand_dims(x, 3)
        results = model.evaluate(x, labels, verbose=0)
        accuracies[k] = results[1]

    return accuracies


def permutation(dataset, labels, model, function_features=None, n_segments=4, n_channels=22, n_features=396, necessary_redimension=False):
    """
    Function to perform different types of permutation according to the XAI definition

    :param dataset: dataset on which evaluate the ablation (if a feature dataset must be evaluated, this dataset should
    be without feature extraction)
    :param labels: labels corresponding to the dataset
    :param model: model on which evaluate the ablation
    :param function_features: function for the feature extraction of the dataset
    :param n_segments: number of segments to be evaluated with XAI
    :param n_channels: number of channels to be evaluated with XAI
    :param n_features: number of features to be extracted with FBCSP
    :param necessary_redimension: boolean to indicate if redimension is necessary
    """

    print("Applying permutation...")
    accuracies_segments = permutation_segments(dataset, labels, model, function_features, n_segments, n_features, necessary_redimension)

    accuracies_channels = permutation_channels(dataset, labels, model, function_features, n_channels, n_features, necessary_redimension)

    return accuracies_segments, accuracies_channels


def permutation_segments(dataset, labels, model, function_features=None, n_segments=4, n_features=396, necessary_redimension=False):
    """
    Function to perform permutation substituting a segment of a channel of a trial with the same segment of the same
    channel of another trial

    :param dataset: dataset on which evaluate the ablation (if a feature dataset must be evaluated, this dataset should
    be without feature extraction)
    :param labels: labels corresponding to the dataset
    :param model: model on which evaluate the ablation
    :param function_features: function for the feature extraction of the dataset
    :param n_segments: number of segments to be evaluated with XAI
    :param n_features: number of features to be extracted with FBCSP
    :param necessary_redimension: boolean to indicate if redimension is necessary
    :return: each value of the array represents the accuracy obtained without the corresponding segment
    """

    # Extract the indexes of the segments

    indexes = extract_indexes_segments(dataset.shape[2], n_segments)
    accuracies = np.empty(n_segments)

    for k in range(n_segments):

        data = copy.deepcopy(dataset)
        start, end = indexes[k]

        # Extract the random new trial, substitute the segment and rebuild the dataset

        list_trials = range(data.shape[0])

        for i in range(data.shape[0]):
            # list_channels = range(data.shape[1])
            for j in range(data.shape[1]):
                actual_trials = [t for t in list_trials if t != i]
                p = np.random.choice(actual_trials)
                # actual_channels = [c for c in list_channels if c != j]
                # q = np.random.choice(actual_channels)
                data[i, j, start:end] = data[p, j, start:end]

        if function_features is not None:
            if function_features.__name__ == "extractFBCSP":
                x = function_features(dataset, labels, n_features)
            else:
                x = function_features(data)
        else:
            x = data

        # Evaluate the difference of accuracy
        if necessary_redimension:
            x = np.expand_dims(x, 3)

        results = model.evaluate(x, labels, verbose=0)
        accuracies[k] = results[1]

    return accuracies


def permutation_channels(dataset, labels, model, function_features=None, n_channels=22, n_features=396, necessary_redimension=False):
    """
    Function to perform permutation substituting a channel with the same channel of another trial

    :param dataset: dataset on which evaluate the ablation (if a feature dataset must be evaluated, this dataset should
    be without feature extraction)
    :param labels: labels corresponding to the dataset
    :param model: model on which evaluate the ablation
    :param function_features: function for the feature extraction of the dataset
    :param n_channels: number of channels to be evaluated with XAI
    :param n_features: number of features to be extracted with FBCSP
    :param necessary_redimension: boolean to indicate if redimension is necessary
    :return: each value of the array represents the accuracy obtained without the corresponding segment
    """

    accuracies = np.empty(n_channels)

    for k in range(n_channels):

        data = copy.deepcopy(dataset)
        list_trials = range(data.shape[0])

        # Select the random new trial, substitute the channel and rebuild the dataset

        for i in range(data.shape[0]):
            actual_trials = [t for t in list_trials if t != i]
            p = np.random.choice(actual_trials)
            data[i, k, :] = data[p, k, :]

        if function_features is not None:
            if function_features.__name__ == "extractFBCSP":
                x = function_features(dataset, labels, n_features)
            else:
                x = function_features(data)
        else:
            x = data

        # Evaluate the difference of accuracies
        if necessary_redimension:
            x = np.expand_dims(x, 3)
        results = model.evaluate(x, labels, verbose=0)
        accuracies[k] = results[1]

    return accuracies


def save(matrix, output):
    with open(output, 'w') as f:

        for element in matrix:
            if isinstance(element, (list, np.ndarray)):
              for i in range(len(element)):
                      if i == len(element)-1:
                          f.write("%f" % element[i])
                      else:
                          f.write("%f," % element[i])
              f.write('\n')
            else:
                f.write("%f\n" % element)
                
    print("\t- Successfully saved in {}".format(output))
