import scipy
from scipy import signal
from scipy.stats import entropy
from sklearn.preprocessing import normalize
from scipy.io import loadmat
import numpy as np
import pywt
from source.FBCSP_V4 import FBCSP_V4


def load_dataset(data_dir, subject, fs=250, start_second=2, signal_length=4, consider_artefacts=True):
    """
    Function for the loading of the dataset corresponding to a subject (and saved according to dataloading.m)

    :param data_dir: directory where data are saved
    :param subject: index of the current subject
    :param fs: sampling frequency of the signal
    :param start_second: second at which consider the start of the signal of interest
    :param signal_length: length of the signal of interest
    :param consider_artefacts: True if trials labeled as artefacts in the dataset are considered, False otherwise
    :return: dataset of the current subject and relative set of labels
    """

    # Retrieve of data

    i = subject
    path_data = data_dir + '/S' + str(i) + '_data.mat'
    path_event = data_dir + '/S' + str(i) + '_label.mat'

    data = loadmat(path_data)['data']
    event_matrix = loadmat(path_event)['event_matrix']

    event_position = event_matrix[:, 0]
    event_type = event_matrix[:, 1]

    positions = []
    labels = []

    # Find the samples at which the signal of interest starts (labeled as 768 and 1023 - if consider_artefacts =
    # True) and followed by label 769 (left hand) or 770 (right hand)

    start_types = [768, 1023 if consider_artefacts is True else None]

    for l in range(len(event_type)):
        if (event_type[l] in start_types) and event_type[l + 1] == 769:
            positions.append(l)
            labels.append(769)

        if (event_type[l] in start_types) and event_type[l + 1] == 770:
            positions.append(l)
            labels.append(770)

    event_start = event_position[positions]

    # Evaluate the samples  window

    end_second = start_second + signal_length
    windows_sample = np.linspace(int(start_second * fs), int(end_second * fs) - 1,
                                 int(end_second * fs) - int(start_second * fs)).astype(int)

    # Creation of the trials matrix and data normalization

    trials = np.zeros((len(event_start), data.shape[1], len(windows_sample)))
    data = data.T

    for j in range(trials.shape[0]):
        trials[j, :, :] = normalize(data[:, event_start[j] + windows_sample], axis=1)

    # Creation of the label list

    new_labels = []
    labels_name = {769: [1, 0], 770: [0, 1]}
    for j in range(len(labels)):
        new_labels.append(labels_name[labels[j]])

    return trials, new_labels


def create_dict(dataset, labels):
    """
    Function for the creation of a dictionary of type {label: trials, label2: trials} for FBCSP class

    :param dataset: whole dataset from which retrieve data
    :param labels: labels corresponding to each trial in the dataset
    :return: dictionary related to the dataset
    """

    # According to its label, each trial is appended to one or the other list

    values1 = []
    values2 = []

    for i in range(len(labels)):
        if (labels[i] == [1, 0]).all():
            values1.append(dataset[i])
        else:
            values2.append(dataset[i])

    # Dictionary creation with the previous lists

    data_dict = {1: np.array(values1), 2: np.array(values2)}

    return data_dict


def extract_indexes_segments(data_length, n_segments):
    """
    Function to extract the sample indexes corresponding to the begin and end of each segment in a signal

    :param data_length: length of the signal to be segmented
    :param n_segments: number of segmented to be obtained from the signal
    :return: list of (start, end) samples, one for each segment
    """

    # Extract the segment length

    segment_length = int(data_length / n_segments)
    indexes = []

    # For each segment, determine the correspondent indexes (checking the position of the end one)

    for k in range(n_segments):

        start = k * segment_length
        end = (k + 1) * segment_length

        if (k + 2) * segment_length > data_length:
            end = data_length

        indexes.append((start, end))

    return indexes


def extract_psd(matrix, fs=250):
    """
    Extract the power spectral density of each channel of each trial inside the data matrix

    :param matrix: data matrix for each the psd will be calculated (n.trials x n.channels x n.samples)
    :param fs: sampling frequency of the data
    :return: matrix containing the psd instead of the signal samples
    """

    fft_dataset = np.zeros((matrix.shape[0], matrix.shape[1], 129))

    for t, trial in enumerate(matrix):

        trial = np.matrix(trial)

        for i in range(trial.shape[0]):

            # For the signals coming from each channel, extract the corresponding psd

            data = trial[i, :]
            freqs, psd = signal.welch(data, fs=fs)
            fft_dataset[t, i, :] = psd

    return np.array(fft_dataset)


def extract_wt(matrix):
    """
    Extract the approximation component obtained with wavelet decomposition of each channel of each trial inside the
    data matrix

    :param matrix: data matrix for each the wavelet will be calculated (n.trials x n.channels x n.samples)
    :return: matrix containing the approximation components of data
    """

    approx_trials = []

    for trial in matrix:
        approx = []

        for channel in trial:

            # For the signals coming from each channel, extract the corresponding wavelet decomposition

            ca, _ = pywt.dwt(channel, 'sym9')

            approx.append(ca)

        approx_trials.append(approx)

    return np.array(approx_trials)


def extract_statistical_characteristics(matrix):
    """
    Extract the statistical characteristics of the channels and between the channels in each trial

    :param matrix: data matrix for each the characteristics will be calculated (n.trials x n.channels x n.samples)
    :return: matrix containing the standard characteristics of data
    """

    sc_dataset = np.zeros((matrix.shape[0], matrix.shape[1], matrix.shape[1] + 10))

    for t, trial in enumerate(matrix):
        trial = np.matrix(trial)

        for i in range(trial.shape[0]):

            # For the signals coming from each channel, extract the corresponding statistical characteristics

            data = trial[i, :]
            sc = scipy.stats.describe(data, axis=1)
            sc_dataset[t, i, 0] = sc.mean
            sc_dataset[t, i, 1] = np.mean(np.square(data))
            sc_dataset[t, i, 2] = sc.variance
            sc_dataset[t, i, 3] = sc.skewness
            sc_dataset[t, i, 4] = sc.kurtosis
            sc_dataset[t, i, 5] = entropy(data, axis=1)
            sc_dataset[t, i, 6] = np.trapz(np.array(data), axis=1)  # area under the (rectified) curve
            sc_dataset[t, i, 7] = len(data) - np.count_nonzero(data)  # number of zero-crossing
            sc_dataset[t, i, 8] = np.max(data) - np.min(data)  # peak-to-peak
            sc_dataset[t, i, 9] = 0  #TODO: trovare un'altra caratteristica statistica

        sc_dataset[t, :, 10:] = np.corrcoef(trial)  # Pearson Correlation Coefficients between channels

    # Replace possible -inf values with -5 (other are between -1 and 1)
    sc_dataset = np.nan_to_num(sc_dataset, neginf=-5)

    return np.array(sc_dataset)


def extractFBCSP(matrix, labels, n_features, fs=250):
    """
    Extraction of the features thanks to FBCSP Class (@author: Alberto Zancanaro)

    :param matrix: data matrix from which extract the features
    :param labels: labels corresponding to the trials in the data matrix
    :param n_features: minimum number of features to be extracted
    :param fs: sampling frequency of data
    :return: data matrix with the features extracted for each trial
    """

    # Creation of the dictionary corresponding to the data matrix

    trials_dict = create_dict(matrix, labels)

    # Extraction of the FBCSP feature for the current dictionary and concatenation (needed because it returns two
    # matrices of features, one for each label

    FBCSP_f = FBCSP_V4(trials_dict, fs, n_w=22, n_features=n_features, print_var=True)
    fbcsp = FBCSP_f.extractFeaturesForTraining()
    fbcsp = np.concatenate((fbcsp[0], fbcsp[1]), axis=0)

    if fbcsp.shape[1] < n_features:
        pad = np.zeros((fbcsp.shape[0], n_features))
        pad[:, :fbcsp.shape[1]] = fbcsp
        fbcsp = pad

    # Reshape for the subsequent training

    fbcsp = fbcsp.reshape((fbcsp.shape[0], 1, fbcsp.shape[1]))

    return np.array(fbcsp)
