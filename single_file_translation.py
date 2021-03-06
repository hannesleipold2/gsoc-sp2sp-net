#standard import
import os, sys
import ffmpeg
import librosa
from moviepy.editor import *
import moviepy.editor as mp

#split silence thing
from pydub import AudioSegment
from pydub.silence import split_on_silence

#translation (google at back)
from deep_translator import GoogleTranslator

#tts from text-to-speech
from text_to_speech import speak
from gtts import gTTS



def read_audio(video_file, audio_file):
	# stream = ffmpeg.input(video_file)
	# stream = ffmpeg.output(stream, audio_file)
	# ffmpeg.run(stream)

	os.system("ffmpeg -i \"" + video_file + "\" -f wav -bitexact -acodec pcm_s16le -ar 16000 -ac 1 \"" + audio_file + "\"")

def wav_to_webm(wav_file, webm_file):
	os.system("ffmpeg -i \"" + wav_file + "\" -acodec libvorbis -aq 5 -ac 2 -qmax 25 " + webm_file)

def change_audio_speed(file1, file2, outfile):
	DURATION_RATIO = 0.001

	duration_in = librosa.get_duration(filename=file1)
	duration_out = librosa.get_duration(filename=file2)

	print("duration_in: ", duration_in)
	print("duration_out: ", duration_out)
	ratio = duration_out / duration_in

	if ratio < DURATION_RATIO:
		ratio = DURATION_RATIO
	# end-tab
	ratio = str(ratio)
	tmp_file = "tmp." + file1.split(".")[-1]
	os.system('ffmpeg -i ' + file1 + ' -filter:a "atempo=' + ratio + '" -vn ' + tmp_file)
	if os.path.isfile(outfile): os.system('rm ' + outfile)
	os.system('mv ' + tmp_file + ' ' + outfile)

class sp2sp_core():

	def __init__(self):
		# SP 2 T (ASR) -> T 2 T (Machine Translate) -> T 2 SP (TTS)
		self.asr 	= "deepspeech"
		self.mt 	= "deeptranslate"
		self.tts 	= "google"

	def asr_deepspeech(self, model, scorer, audio):
		os.system("deepspeech --model " + model + " --scorer " + scorer + " --audio " + audio + " > a.txt")
		text = open("a.txt", 'r').read()
		os.system("rm a.txt")
		return text

	def txt_to_sp(self, out_file, text, lang):
		tts = gTTS(text=text, lang=lang)
		tts.save(out_file)

	"""
		params:
	"""
	def translate(self, source, slang='en', tlang='fr'):
		'''
		source: input string
		source_lang: en
		target_lang: fr
		'''
		target = GoogleTranslator(source=slang, target=tlang).translate(source)
		return target

	def create_final_video(self, original_video, final, audio):
		vclip = VideoFileClip(original_video)
		vdur = vclip.duration
		aclip = AudioFileClip(audio)
		adur = aclip.duration

		if vdur >= adur:
			vsub = vclip.subclip(0,adur)
			videoclip1 = vsub.set_audio(aclip)
			videoclip2 = vclip.subclip((vdur-adur), vdur).without_audio()
			videoclip = mp.concatenate_videoclips([videoclip1, videoclip2], method="compose")
		else:
			asub = aclip.subclip(0,vdur)
			videoclip = vclip.set_audio(asub)
		# end-tab

		print("video clip duration", videoclip.duration)
		videoclip.write_videofile(final)


if __name__ == '__main__':

	asr_model = "./project/translate/pretrained_models/asr_deepspeech/deepspeech-0.9.3-models.pbmm"
	asr_scorer = "./project/translate/pretrained_models/asr_deepspeech/deepspeech-0.9.3-models.scorer"

	sp2sp_handler = sp2sp_core()

	given_input = 	sys.argv[1]
	given_out 	=	sys.argv[2]
	INPUT_LANG 	= 	'en' 		if len(sys.argv) < 4 else sys.argv[3]
	OUTPUT_LANG = 	'fr' 		if len(sys.argv) < 5 else sys.argv[4]
	IS_REAL_VIDEO = 0 			if len(sys.argv) < 6 else int(sys.argv[5])

	""" RUN PYAUDIO ANALYSIS TO CREATE CHUNKS"""
	USE_SPLITTER 	= 0
	SPLITTER_WEIGHT = 0.3	# between 0 and 1
	SPLITTER_WINDOW	= 30 	# in seconds


	cmd = "python ./pyAudioAnalysis/pyAudioAnalysis/audioAnalysis.py " + \
		  "silenceRemoval -i ./new-home-in-the-stars-16k.wav -s " + \
		  str(SPLITTER_WINDOW) + " -w" + str(SPLITTER_WEIGHT)

	if len(sys.argv) < 3:
		print("ERROR! NOT ENOUGH ARGS!")
		print("PLEASE GIVE: \n"
			  "1. INPUT AUDIO/VIDEO FILE \n"
			  "2. DESIRED OUTPUT FILE NAME \n"
			  "3. INPUT LANGUAGE (optional) \n"
			  "4. OUTPUT LANGUAGE (optional) \n"
			  "5. AUDIO OR VIDEO (default = AUDIO)")
		sys.exit()
	# end-tab

	print("IN AND OUT")
	print(given_input)
	print(given_out)

	audio_input = os.path.basename(given_input).split(".")[0] + ".wav"
	audio_out = os.path.basename(given_out).split(".")[0] + ".wav"
	read_audio(given_input, audio_input)

	text_from_speech = sp2sp_handler.asr_deepspeech(model=asr_model, scorer=asr_scorer, audio=audio_input)
	print("Transrciption: ")
	print(text_from_speech)

	text_translated = sp2sp_handler.translate(text_from_speech, INPUT_LANG, OUTPUT_LANG)
	p = str(text_translated)
	print("Translated Transcription: ")
	print(p)

	sp2sp_handler.txt_to_sp(out_file=audio_out, text=p,lang=OUTPUT_LANG)
	change_audio_speed(file1=audio_out, file2=audio_input, outfile=audio_out)
	if not IS_REAL_VIDEO:
		wav_to_webm(audio_out, given_out)
		os.system("rm " + audio_input)
		os.system("rm " + audio_out)
	else:
		sp2sp_handler.create_final_video(original_video=given_input, final=given_out, audio=audio_out)
		os.system("rm " + audio_input)
		os.system("rm " + audio_out)
	# end-tab

