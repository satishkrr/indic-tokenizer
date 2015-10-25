#!/usr/bin/env python
# -*- coding=utf-8 -*-

import re
import sys
import argparse
import os.path

ENCHANT = True

try:
    import enchant
except ImportError:
    ENCHANT = False

class tokenizer():
    def __init__(self, lang='hin'):
        self.lang = lang
        self.WORD_JOINER=u'\u2060'
        self.SOFT_HYPHEN=u'\u00AD'
        self.BYTE_ORDER_MARK=u'\uFEFF'
        self.BYTE_ORDER_MARK_2=u'\uFFFE'
        self.NO_BREAK_SPACE=u'\u00A0'
        self.ZERO_WIDTH_SPACE=u'\u200B'
        self.ZERO_WIDTH_JOINER=u'\u200D'
        self.ZERO_WIDTH_NON_JOINER=u'\u200C'

        file_path = os.path.abspath(__file__).rpartition('/')[0]
        if ENCHANT:
            self.en_dict = enchant.Dict('en_US')

        self.ben = lang in ["ben", "asm"]
        self.dev = lang in ["hin", "mar", "nep", "bod", "kok"]
	self.tam = lang == 'tam'
	self.tel = lang == 'tel'
	self.mal = lang == 'mal'
	self.kan = lang == 'kan'
	self.guj = lang == 'guj'
	self.pan = lang == 'pan'
	self.ori = lang == 'ori'

        #load nonbreaking prefixes from file
	with open('%s/NONBREAKING_PREFIXES' %file_path) as fp:
	    self.NBP = dict()
	    for line in fp:
		if not line.startswith('#'):
		    if '#NUMERIC_ONLY#' in line:
			self.NBP[line.replace('#NUMERIC_ONLY#', '').split()[0]] = 2
		    else:
			self.NBP[line.strip()] = 1

    def normalize(self,text):
        """
        Performs some common normalization, which includes: 
            - Byte order mark, word joiner, etc. removal 
            - ZERO_WIDTH_NON_JOINER and ZERO_WIDTH_JOINER removal 
            - ZERO_WIDTH_SPACE and NO_BREAK_SPACE replaced by spaces 
        """

        text=text.replace(self.BYTE_ORDER_MARK,'')
        text=text.replace(self.BYTE_ORDER_MARK_2,'')
        text=text.replace(self.WORD_JOINER,'')
        text=text.replace(self.SOFT_HYPHEN,'')

        text=text.replace(self.ZERO_WIDTH_SPACE,' ') 
        text=text.replace(self.NO_BREAK_SPACE,' ')

        text=text.replace(self.ZERO_WIDTH_NON_JOINER, '')
        text=text.replace(self.ZERO_WIDTH_JOINER,'')

        return text

    def tokenize(self, text):
        text = ' %s ' %' '.join(text.split())
        # remove junk characters
        text = re.sub('[\x00-\x1f]', '', text)
        # seperate out on Latin-1 supplementary characters
        text = re.sub(u'([\xa1-\xbf\xd7\xf7])', r' \1 ', text)        
        # seperate out on general unicode punctituations except "’"
        text = re.sub(u'([\u2000-\u2018\u201a-\u206f])', r' \1 ', text)        
        # seperate out on unicode mathematical operators
        text = re.sub(u'([\u2200-\u22ff])', r' \1 ', text)        
        # seperate out on unicode fractions
        text = re.sub(u'([\u2150-\u2160])', r' \1 ', text)        
        # seperate out on unicode superscripts and subscripts
        text = re.sub(u'([\u2070-\u209f])', r' \1 ', text)        
        # seperate out on unicode currency symbols
        text = re.sub(u'([\u20a0-\u20cf])', r' \1 ', text)        
        # seperate out all "other" special characters
        text = re.sub(u"([^\u0080-\U0010ffffa-zA-Z0-9\s\.'`,-])", r' \1 ', text)        

        #keep multiple dots together
        text = re.sub(r'(\.\.+)([^\.])', lambda m: r' %sMULTI %s' %('DOT'*len(m.group(1)), m.group(2)), text)
        #keep multiple purna-viram together
        text = re.sub(u'(\u0964\u0964+)([^\u0964])', lambda m: r' %sMULTI %s' %('PNVM'*len(m.group(1)), m.group(2)), text)
        #keep multiple purna deergh-viram together
        text = re.sub(u'(\u0965\u0965+)([^\u0965])', lambda m: r' %sMULTI %s' %('DGVM'*len(m.group(1)), m.group(2)), text)
        #seperate out "," except for Hindi and Ascii digits
        text = re.sub(u'([^0-9\u0966-\u096f]),', r'\1 , ', text)
        text = re.sub(u',([^0-9\u0966-\u096f])', r' , \1', text)
        #split contractions right (both "'" and "’")
        text = re.sub(u"([^a-zA-Z\u0080-\u024f])(['\u2019])([^a-zA-Z\u0080-\u024f])", r"\1 \2 \3", text)
        text = re.sub(u"([^a-zA-Z0-9\u0966-\u096f\u0080-\u024f])(['\u2019])([a-zA-Z\u0080-\u024f])", r"\1 \2 \3", text)
        text = re.sub(u"([a-zA-Z\u0080-\u024f])(['\u2019])([^a-zA-Z\u0080-\u024f])", r"\1 \2 \3", text)
        text = re.sub(u"([a-zA-Z\u0080-\u024f])(['\u2019])([a-zA-Z\u0080-\u024f])", r"\1 \2\3", text)
        text = re.sub(u"([0-9\u0966-\u096f])(['\u2019])s", r"\1 \2s", text)
        text = text.replace("''", " ' ' ")

        #handle non-breaking prefixes
        words = text.split()
        text_len = len(words) - 1
        text = str()
        for i,word in enumerate(words):
            if word.endswith('.'):
                dotless = word[:-1]
                if dotless.isdigit():
                    word = dotless + ' .'
                elif ('.' in dotless and re.search('[a-zA-Z]', dotless)) or \
                    self.NBP.get(dotless, 0) == 1 or (i<text_len and words[i+1][0].islower()): pass
                elif self.NBP.get(dotless, 0) == 2 and (i<text_len and words[i+1][0].isdigit()): pass
                elif i < text_len and words[i+1][0].isdigit():
                    if not ENCHANT: pass
                    elif ((len(dotless) > 2) and (self.en_dict.check(dotless.lower()) or \
                        self.en_dict.check(dotless.title()))):
                        word = dotless + ' .'
                else: word = dotless + ' .'
            text += "%s " %word

        #separate out on Hindi characters except digits followed by non-Indic characters or purna viram or deergh viram
        if self.dev:
            text = re.sub(u'([\u0900-\u0965\u0970-\u097f])([^\u0900-\u0965\u0970-\u097f]|[\u0964\u0965])', r'\1 \2', text)
            text = re.sub(u'([^\u0900-\u0965\u0970-\u097f]|[\u0964\u0965])([\u0900-\u0965\u0970-\u097f])', r'\1 \2', text)
        elif self.ben:
            text = re.sub(u'([\u0980-\u09e5\u09f0-\u09ff])([^\u0980-\u09e5\u09f0-\u09ff]|[\u0964-\u0965])', r'\1 \2', text)
            text = re.sub(u'([^\u0980-\u09e5\u09f0-\u09ff]|[\u0964-\u0965])([\u0980-\u09e5\u09f0-\u09ff])', r'\1 \2', text)
            #seperate out Bengali special chars (currency signs, BENGALI ISSHAR)
            text = re.sub(u'([\u09f2\u09f3\u09fa\u09fb])', r' \1 ', text)
        elif self.guj:
            text = re.sub(u'([\u0A80-\u0AE5\u0Af0-\u0Aff])([^\u0A80-\u0AE5\u0Af0-\u0Aff]|[\u0964-\u0965])', r'\1 \2', text)
            text = re.sub(u'([^\u0A80-\u0AE5\u0Af0-\u0Aff]|[\u0964-\u0965])([\u0A80-\u0AE5\u0Af0-\u0Aff])', r'\1 \2', text)
            #seperate out Gujurati special chars (currency signs, GUJARATI OM)
            text = re.sub(u'([\u0AD0\u0AF1])', r' \1 ', text)
        elif self.mal:
            text = re.sub(u'([\u0D00-\u0D65\u0D73-\u0D7f])([^\u0D00-\u0D65\u0D73-\u0D7f]|[\u0964-\u0965])', r'\1 \2', text)
            text = re.sub(u'([^\u0D00-\u0D65\u0D73-\u0D7f]|[\u0964-\u0965])([\u0D00-\u0D65\u0D73-\u0D7f])', r'\1 \2', text)
            #seperate out Malayalam fraction symbols
            text = re.sub(u'([\u0d73\u0d74\u0d75])', r' \1 ', text)
        elif self.pan:
            text = re.sub(u'([\u0A00-\u0A65\u0A70-\u0A7f])([^\u0A00-\u0A65\u0A70-\u0A7f]|[\u0964-\u0965])', r'\1 \2', text)
            text = re.sub(u'([^\u0A00-\u0A65\u0A70-\u0A7f]|[\u0964-\u0965])([\u0A00-\u0A65\u0A70-\u0A7f])', r'\1 \2', text)
        elif self.tel:
            text = re.sub(u'([\u0c00-\u0c65\u0c70-\u0c7f])([^\u0c00-\u0c65\u0c70-\u0c7f]|[\u0964-\u0965])', r'\1 \2', text)
            text = re.sub(u'([^\u0c00-\u0c65\u0c70-\u0c7f]|[\u0964-\u0965])([\u0c00-\u0c65\u0c70-\u0c7f])', r'\1 \2', text)
            #separate out Telugu fractions and weights
            text = re.sub(u'([\u0c78-\u0c7f])', r' \1 ', text)
        elif self.tam:
            text = re.sub(u'([\u0B80-\u0Be5\u0Bf3-\u0Bff])([^\u0B80-\u0Be5\u0Bf3-\u0Bff]|[\u0964-\u0965])', r'\1 \2', text)
            text = re.sub(u'([^\u0B80-\u0Be5\u0Bf3-\u0Bff]|[\u0964-\u0965])([\u0B80-\u0Be5\u0Bf3-\u0Bff])', r'\1 \2', text)
            #seperate out Tamil special symbols (calendrical, clerical, currency signs etc.)
            text = re.sub(u'([\u0bd0\u0bf3-\u0bff])', r' \1 ', text)
        elif self.kan:
            text = re.sub(u'([\u0C80-\u0Ce5\u0Cf1-\u0Cff])([^\u0C80-\u0Ce5\u0Cf1-\u0Cff]|[\u0964-\u0965])', r'\1 \2', text)
            text = re.sub(u'([^\u0C80-\u0Ce5\u0Cf1-\u0Cff]|[\u0964-\u0965])([\u0C80-\u0Ce5\u0Cf1-\u0Cff])', r'\1 \2', text)
        elif self.ori:
            text = re.sub(u'([\u0B00-\u0B65\u0B70-\u0B7f])([^\u0B00-\u0B65\u0B70-\u0B7f]|[\u0964-\u0965])', r'\1 \2', text)
            text = re.sub(u'([^\u0B00-\u0B65\u0B70-\u0B7f]|[\u0964-\u0965])([\u0B00-\u0B65\u0B70-\u0B7f])', r'\1 \2', text)
            #seperate out Oriya fraction symbols
	    text = re.sub(u'([\u0B72-\u0B77])', r' \1 ', text)

        #Normalize "|" to purna viram 
        text = text.replace('|', u'\u0964')
        #Normalize ". ।" to "।"
        text = re.sub(u'\.\s+\u0964', u'\u0964', text)
       
        text = re.sub('(-+)', lambda m: r'%s' %(' '.join('-'*len(m.group(1)))), text) 
        if self.dev:
            text = re.sub(u'(-?[0-9\u0966-\u096f]-+[0-9\u0966-\u096f]-?){,}',lambda m: r'%s' %(m.group().replace('-', ' - ')), text)
        elif self.ben:
            text = re.sub(u'(-?[0-9\u09e6-\u09ef]-+[0-9\u09e6-\u09ef]-?){,}',lambda m: r'%s' %(m.group().replace('-', ' - ')), text)
        elif self.guj:
            text = re.sub(u'(-?[0-9\u0ae6-\u0aef]-+[0-9\u0ae6-\u0aef]-?){,}',lambda m: r'%s' %(m.group().replace('-', ' - ')), text)
        elif self.mal:
            text = re.sub(u'(-?[0-9\u0d66-\u0D72]-+[0-9\u0d66-\u0D72]-?){,}',lambda m: r'%s' %(m.group().replace('-', ' - ')), text)
        elif self.pan:
            text = re.sub(u'(-?[0-9\u0a66-\u0a6f]-+[0-9\u0a66-\u0a6f]-?){,}',lambda m: r'%s' %(m.group().replace('-', ' - ')), text)
        elif self.tel:
            text = re.sub(u'(-?[0-9\u0c66-\u0c6f]-+[0-9\u0c66-\u0c6f]-?){,}',lambda m: r'%s' %(m.group().replace('-', ' - ')), text)
        elif self.tam:
            text = re.sub(u'(-?[0-9\u0be6-\u0bf2]-+[0-9\u0be6-\u0bf2]-?){,}',lambda m: r'%s' %(m.group().replace('-', ' - ')), text)
        elif self.kan:
            text = re.sub(u'(-?[0-9\u0ce6-\u0cef]-+[0-9\u0ce6-\u0cef]-?){,}',lambda m: r'%s' %(m.group().replace('-', ' - ')), text)
        elif self.ori:
            text = re.sub(u'(-?[0-9\u0b66-\u0b6f]-+[0-9\u0b66-\u0b6f]-?){,}',lambda m: r'%s' %(m.group().replace('-', ' - ')), text)
        text = ' '.join(text.split())
        #restore multiple dots, purna virams and deergh virams
        text = re.sub(r'(DOT)(\1*)MULTI', lambda m: r'.%s' %('.'*(len(m.group(2))/3)), text)
        text = re.sub(r'(PNVM)(\1*)MULTI', lambda m: u'\u0964%s' %(u'\u0964'*(len(m.group(2))/4)), text)
        text = re.sub(r'(DGVM)(\1*)MULTI', lambda m: u'\u0965%s' %(u'\u0965'*(len(m.group(2))/4)), text)

	#split sentences
	text = re.sub(u' ([!.?\u0964\u0965]) ', r' \1\n', text)
        
        return text

if __name__ == '__main__':
    
    lang_help = """select language (3 letter ISO-639 code)
		Hindi       : hin
		Telugu      : tel
		Tamil       : tam
		Malayalam   : mal
		Kannada     : kan
		Bengali     : ben
		Oriya       : ori
		Punjabi     : pan
		Marathi     : mar
		Nepali      : nep
		Gujarati    : guj
		Bodo        : bod
		Konkani     : kok
		Assamese    : asm"""
    languages = "hin ben asm guj mal pan tel tam kan ori mar nep bod kok".split()
    # parse command line arguments 
    parser = argparse.ArgumentParser(prog="indic_tokenizer", 
                                    description="Tokenizer for Indian Scripts",
                                    formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--i', metavar='input', dest="INFILE", type=argparse.FileType('r'), default=sys.stdin, help="<input-file>")
    parser.add_argument('--l', metavar='language', dest="lang", choices=languages, default='hin', help=lang_help)
    parser.add_argument('--o', metavar='output', dest="OUTFILE", type=argparse.FileType('w'), default=sys.stdout, help="<output-file>")
    args = parser.parse_args()

    # initialize convertor object
    tzr = tokenizer(lang=args.lang)
    # convert data
    for line in args.INFILE:
        line = line.decode('utf-8')
        line = tzr.normalize(line)
        line = tzr.tokenize(line)
        line = line.encode('utf-8')
        args.OUTFILE.write('%s\n' %line)

    # close files 
    args.INFILE.close()
    args.OUTFILE.close()
