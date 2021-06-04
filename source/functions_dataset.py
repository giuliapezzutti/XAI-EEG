from EEGModels import EEGNet
from matplotlib import pyplot as plt
from scipy.io import loadmat
import numpy as np
from numpy.fft import rfft
import pywt


def load_dataset(data_dir, subject, fs=250, start_second=2, signal_length=4, consider_artefacts=True):

    i = subject

    path_data = data_dir + '/S' + str(i) + '_data.mat'
    path_event = data_dir + '/S' + str(i) + '_label.mat'

    data = loadmat(path_data)['data']
    event_matrix = loadmat(path_event)['event_matrix']

    event_position = event_matrix[:, 0]
    event_type = event_matrix[:, 1]

    positions = []
    labels = []

    start_types = [768, 1023 if consider_artefacts is True else None]

    for l in range(len(event_type)):
        if (event_type[l] in start_types) and event_type[l + 1] == 769:
            positions.append(l)
            labels.append(769)

        if (event_type[l] in start_types) and event_type[l + 1] == 770:
            positions.append(l)
            labels.append(770)

    event_start = event_position[positions]

    # Evaluate the samples for the trial window
    end_second = start_second + signal_length
    windows_sample = np.linspace(int(start_second * fs), int(end_second * fs) - 1,
                                 int(end_second * fs) - int(start_second * fs)).astype(int)

    # Create the trials matrix
    trials = np.zeros((len(event_start), data.shape[1], len(windows_sample)))
    data = data.T

    for j in range(trials.shape[0]):
        trials[j, :, :] = data[:, event_start[j] + windows_sample]

    new_labels = []
    labels_name = {769: 1, 770: 2}
    for j in range(len(labels)):
        new_labels.append(labels_name[labels[j]])
    labels = new_labels

    return trials, labels


def create_dict(dataset, classes, labels_name):

    values0 = values1 = []

    for i in range(len(classes)):
        if classes[i] == 1:
            values0.append(dataset[i])
        else:
            values1.append(dataset[i])

    dict = {labels_name[1]: np.stack(values0), labels_name[2]: np.stack(values1)}
    return dict


def extract_FFT(matrix):
    fft_mat = []

    for trial in matrix:
        trial = np.matrix(trial)
        fft_trial = np.empty((trial.shape[0], 501))

        for i in range(trial.shape[0]):
            data = fft_trial[i, :]
            fft_trial[i, :] = np.abs(np.fft.fft(data)) ** 2

        fft_mat.append(fft_trial)

    return np.array(fft_mat)


def extract_wt(matrix):
    approx_trials = []
    for trial in matrix:
        approx = []
        for channel in trial:
            cA, cD = pywt.dwt(channel, 'db1')
            approx.append(np.concatenate((cA, cD)))
        approx_trials.append(approx)
    return np.array(approx_trials)