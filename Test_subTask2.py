import os
import keras
import numpy as np
import pandas as pd
import re
from bs4 import BeautifulSoup
from keras.preprocessing.text import Tokenizer
from keras.preprocessing.sequence import pad_sequences
from keras.utils.np_utils import to_categorical
from keras.layers import Dense, Input
from keras.layers import  Embedding, LSTM, Bidirectional
from keras.models import  Model
from Attention_layer import Attention_layer


QUESTION_MAX_SEQUENCE_LENGTH = 80
ANSWER_MAX_SEQUENCE_LENGTH = 100
EMBEDDING_DIM = 100
VALIDATION_SPLIT = 0.2


def clean_str(string):
    string = re.sub(r"\\", "", string)
    string = re.sub(r"\'", "", string)
    string = re.sub(r"\"", "", string)
    return string.strip().lower()

data_train = pd.read_csv('label_answer.csv', sep='\t')
print data_train.shape
question_list = []
answer_list = []
labels_list = []

embeddings_index = {}
f = open('glove.6B.100d.txt')
for line in f:
    values = line.split()
    word = values[0]
    coefs = np.asarray(values[1:], dtype='float32')
    embeddings_index[word] = coefs
f.close()

for idx in range(data_train.label.shape[0]):
    question = BeautifulSoup(data_train.question[idx], "lxml")
    answer = BeautifulSoup(data_train.answer[idx], "lxml")
    question_list.append(clean_str(question.get_text().encode('ascii','ignore')))
    answer_list.append(clean_str(answer.get_text().encode('ascii', 'ignore')))
    labels_list.append(data_train.label[idx])

labels = to_categorical(np.asarray(labels_list),num_classes=3)


question_tokenizer = Tokenizer(nb_words=None)
question_tokenizer.fit_on_texts(question_list)
question_sequences = question_tokenizer.texts_to_sequences(question_list)
question_word_index = question_tokenizer.word_index

answer_tokenizer = Tokenizer(nb_words=None)
answer_tokenizer.fit_on_texts(answer_list)
answer_sequences = answer_tokenizer.texts_to_sequences(answer_list)
answer_word_index = answer_tokenizer.word_index

question_data = pad_sequences(question_sequences, maxlen=QUESTION_MAX_SEQUENCE_LENGTH)
answer_data = pad_sequences(answer_sequences, maxlen=ANSWER_MAX_SEQUENCE_LENGTH)

# shuffle list
indices = np.arange(question_data.shape[0])
np.random.shuffle(indices)
question_data = question_data[indices]
answer_data = answer_data[indices]
labels = labels[indices]

question_embedding_matrix = np.random.random((len(question_word_index) + 1, EMBEDDING_DIM))
for word, i in question_word_index.items():
    embedding_vector = embeddings_index.get(word)
    if embedding_vector is not None:
        # words not found in embedding index will be all-zeros.
        question_embedding_matrix[i] = embedding_vector

answer_embedding_matrix = np.random.random((len(answer_word_index) + 1, EMBEDDING_DIM))
for word, i in answer_word_index.items():
    embedding_vector = embeddings_index.get(word)
    if embedding_vector is not None:
        # words not found in embedding index will be all-zeros.
        answer_embedding_matrix[i] = embedding_vector



question_embedding_layer = Embedding(len(question_word_index) + 1,
                            EMBEDDING_DIM,
                            weights=[question_embedding_matrix],
                            mask_zero=False,
                            input_length=QUESTION_MAX_SEQUENCE_LENGTH,trainable=False)

answer_embedding_layer = Embedding(len(answer_word_index) + 1,
                            EMBEDDING_DIM,
                            weights=[answer_embedding_matrix],
                            mask_zero=False,
                            input_length=ANSWER_MAX_SEQUENCE_LENGTH,trainable=False)

# process question
question_input = Input(shape=(80,), dtype='int32')
embedded_question = question_embedding_layer(question_input)
question_gru = Bidirectional(LSTM(100, return_sequences=True))(embedded_question)
question_att = Attention_layer()(question_gru)

# process answer
answer_input = Input(shape=(100,), dtype='int32')
embedded_answer = answer_embedding_layer(answer_input)
answer_gru = Bidirectional(LSTM(100, return_sequences=True))(embedded_answer)
answer_att = Attention_layer()(answer_gru)

# concatenate question and answer
concatenate_layer= keras.layers.Concatenate(axis=-1)([question_att, answer_att])

dense_1 = Dense(100,activation='tanh')(concatenate_layer)

dense_2 = Dense(3, activation='softmax')(dense_1)

model = Model([question_input,answer_input], dense_2)

model.compile(loss='categorical_crossentropy',
              optimizer='rmsprop',
              metrics=['accuracy'])

model.summary()

model.fit([question_data,answer_data],labels,validation_split=VALIDATION_SPLIT,nb_epoch=20,batch_size=256)
