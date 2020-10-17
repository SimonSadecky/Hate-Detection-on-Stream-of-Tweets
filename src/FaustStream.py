#!/usr/bin/env python
# coding: utf-8

import re
import string
from string import ascii_lowercase
from unidecode import unidecode

def cleanText(sentence):

	sentence = sentence.lower()
	
	sentence = re.sub(r'https?:\/\/.*?["|;| ]', '  ', sentence)
	sentence = re.sub(r'https?:\/\/.*?$', '  ', sentence)
	sentence = re.sub(r'&.+?;', ' ', sentence)
	sentence = re.sub(r'^rt | rt | rt$',' ' , sentence)
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
    
	return sentence

import faust
import json

app = faust.App('FaustStream', broker='kafka://localhost:9092', value_serializer='raw')
kafka_topic = app.topic('HateSpeechStream')

@app.agent(kafka_topic)
async def TweetProcessing(data):
	async for tweet in data:
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
					tweet = cleanText(tweet["full_text"])
					print(tweet)
				except:
					try:
						tweet = cleanText(tweet["text"])
						print(tweet)
					except:
						continue
		else:
			continue
