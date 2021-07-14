import sys
from functions_dataset import *
from functions_network import *
from sklearn.model_selection import train_test_split
import numpy as np
import tensorflow as tf
import os

if __name__ == "__main__":

    data_dir = '../dataset/EEG'

    n_segments = 8  # number of segments considered in the signal
    n_features = 396  # number of features for FBCSP
    fs = 250  # sampling frequency
    tot_accuracies = []
    zero_accuracies = []
    interpolation_accuracies = []
    channel_accuracies = []

    # sys.stdout = open("../output/output - {} segments.txt".format(n_segments), "w")  # TO WRITE ALL OUTPUT IN A FILE

    subjects = range(1, 10, 1)  # dataset composition
    dataset, labels = None, None

    for subject in subjects:

        if dataset is None:
            dataset, labels = load_dataset(data_dir, subject, consider_artefacts=False)

        else:
            d, l = load_dataset(data_dir, subject, consider_artefacts=False)
            dataset = np.concatenate((dataset, np.array(d)), axis=0)  # complete dataset
            labels = np.concatenate((labels, np.array(l)), axis=0)

    # Common hyperparameters for the training

    batch_size = 32
    num_epochs = 50

    labels = np.array(labels)

    iteractions = 100
    for i in range(iteractions):
        train_dataset, test_dataset, train_labels, test_labels = train_test_split(dataset, labels, train_size=0.7)
        wavelet_variation(train_dataset[0][0])

        train_wt = extract_wt(train_dataset)
        test_wt = extract_wt(test_dataset)

        # if not os.path.exists('../models/EEGNet_wt.h5'):
        model = training_EEGNet(train_wt, train_labels, batch_size=batch_size, num_epochs=num_epochs,
                                model_path='../models/EEGNet_wt')
        # else:
        #     model = tf.keras.models.load_model('../models/EEGNet_wt.h5')

        results = model.evaluate(test_wt, test_labels, verbose=0)
        tot_accuracies.append(results[1])

        accuracies = ablation(test_dataset, test_labels, model, extract_wt, n_segments)
        zero_accuracies.append(list(accuracies[0]))
        interpolation_accuracies.append(list(accuracies[1]))
        channel_accuracies.append(list(accuracies[2]))

        # ablation_label_depending(test_dataset, test_labels, model, extract_wt, n_segments)
        #
        # permutation(test_dataset, test_labels, model, extract_wt, n_segments)

    # sys.stdout.close()

    save(tot_accuracies, "../output/tot_accuracies.csv")
    save(zero_accuracies, "../output/zero_accuracies.csv")
    save(interpolation_accuracies, "../output/interpolation_accuracies.csv")
    save(channel_accuracies, "../output/channel_accuracies.csv")
