#!/usr/bin/env python
# coding: utf-8


import faust
import json
import numpy as np

app = faust.App('FaustStream', broker='kafka://localhost:9092', value_serializer='raw')
kafka_topic = app.topic('HateSpeechStream')

#-----------------------------------------------------------------------------------------

import csv
import re

def outToCSV(text):	

	with open('HateTweets.csv','a', encoding="utf-8", newline='') as of:
		writer = csv.writer(of, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
		writer.writerow(['1', text])
	of.close()

#-----------------------------------------------------------------------------------------

import ktrain
BERT = ktrain.load_predictor("NN_models\\BERT_predictor")

@app.agent(sink=[outToCSV])
async def DetectHate(final):
	async for HateTweet in final:
		HateTweet = HateTweet.decode('utf-8')
		pred = BERT.predict(HateTweet)
		probability = pred[1]; probability = probability[1]
		
		if float(probability) >  0.9:
			yield HateTweet

#-----------------------------------------------------------------------------------------

import pickle
word_index = pickle.load(open("pickles\\word_index.pickle", 'rb'))

from tensorflow import keras
model = keras.models.load_model('NN_models\\LSTM-CNN_Vinf.h5')
modelB = keras.models.load_model('NN_models\\BiLSTM-LSTM_Vinf.h5')

@app.agent(sink=[DetectHate])
async def PreDetection(stream):
	async for Tweet in stream:
		try:
			Tweet = Tweet.decode('utf-8')
			Tweet = json.loads(Tweet, strict = False)
			tweet_tokens = nltk.word_tokenize(Tweet["clean"])
			sequence = []
			x = 0
			for tok in tweet_tokens:
				try:
					val = word_index[tok]
					if val < 12000:
						sequence.append(word_index[tok])
					else:
						sequence.append(1)
				except:
					sequence.append(1)
				x = x + 1
			for i in range(x, 128):
				sequence.append(0)
			input = np.expand_dims(sequence, axis=0)
			
			prediction = modelB.predict(input)
		except:
			continue
		classification = re.sub(r'\[|\]', '', str(prediction))
		
		if float(classification) > 0.9:
			prediction2 = model.predict(input)
			classification2 = re.sub(r'\[|\]', '', str(prediction2))
			if float(classification) > 0.9:
				yield Tweet["original"]

#-----------------------------------------------------------------------------------------

import string
from string import ascii_lowercase
from unidecode import unidecode

def cleanText(sentence):

	sentence = sentence.lower()
	
	sentence = re.sub(r'https?:\/\/.*?["|;| ]', '  ', sentence)
	sentence = re.sub(r'https?:\/\/.*?$', '  ', sentence)
	sentence = re.sub(r'&.+?;', ' ', sentence)
	sentence = re.sub(r'#.*? |#.*?$',' ' , sentence)
	sentence = re.sub(r'@.*? |@.*?:|@.*?$',' ' , sentence)
	sentence = re.sub(r':|\'|%|_|-', ' ', sentence)
	sentence = re.sub(r'\w*\d+\w*', ' ', sentence)
	sentence = re.sub(r'ha[ha]+|aha[ha]+', 'haha', sentence)
	sentence = re.sub(r'lol[ol]*', 'lol', sentence)
	
	sentence = re.compile(r'(.)\1{2,}').sub(r'\1', sentence)
	sentence = unidecode(sentence)
	
	sentence = re.sub(r'\W+| ', ' ', sentence)
	sentence = re.sub(r' +',' ', sentence)
	sentence = re.sub(r' $|^ ', '', sentence)
    
	sentence = preProcess(sentence)
	
	return sentence

import nltk
from nltk.corpus import stopwords
from nltk.tokenize.treebank import TreebankWordDetokenizer

stop_words = set(stopwords.words('english'))
extended_stops = {"ya", "yo", "yu", "da", "em", "im", "theres", "dat", "dats", "aint", "thats", "doe", "ur"}
negatives = ["no", "none", "not"]

from itertools import groupby    

def preProcess(sentence):
	word_tokens = nltk.word_tokenize(sentence)
	filtered_sentence = []
	
	for w in word_tokens:
		if w not in stop_words and w not in extended_stops and len(w) > 1 or w in negatives:
			filtered_sentence.append(w)
			
	filtered_sentence = [j[0] for j in groupby(filtered_sentence)]
	filtered_sentence = TreebankWordDetokenizer().detokenize(filtered_sentence)

	return filtered_sentence


@app.agent(kafka_topic, sink=[PreDetection])
async def TweetProcessing(data):
	async for TwitterData in data:
	
		tweet = TwitterData
		tweet = tweet.decode('utf-8')
		tweet = json.loads(tweet)
		
		EN = 0
		
		try:
			if tweet["lang"] == "en":
				EN = True
			else:
				EN = False
		except:
			continue
			
		if EN:
			try:
				tweet["retweeted_status"]
			except:
				try:
					tweet = tweet["extended_tweet"]
					original = tweet["full_text"]
					tweet = cleanText(tweet["full_text"])
					Output = "{\"original\":\""+original+"\",\"clean\":\""+tweet+"\"}"
					
					yield Output
				except:
					try:
						original = tweet["text"]
						tweet = cleanText(tweet["text"])					
						Output = "{\"original\":\""+original+"\",\"clean\":\""+tweet+"\"}"

						yield Output
					except:
						continue
		else:
			continue