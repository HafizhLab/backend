import json
import pickle
import random
import sys

from django.db.models.functions import Length
from django.http import HttpResponseBadRequest, JsonResponse

from hafizhlab.quran.models import Ayah, Juz, Surah

sys.path.append('machinelearning')

with open('machinelearning/lm_alquran.pickle', 'rb') as f:
    trained_model = pickle.load(f)

with open('machinelearning/tfidf_alquran.pickle', 'rb') as f:
    trained_model2 = pickle.load(f)

with open('machinelearning/ayahData.json') as f:
    ayah_korpus = json.load(f)['data']


def get_questions(request):
    mode = request.GET['mode']
    scope_type = request.GET['type']
    scope_id = request.GET['number']

    if scope_type.lower() == 'juz':
        scope = Juz.objects.get(id=scope_id)
    elif scope_type.lower() == 'surah':
        scope = Surah.objects.get(id=scope_id)
    else:
        return HttpResponseBadRequest(
            "type must either 'juz' or 'surah'"
        )

    ayah_q = scope.ayah_set.annotate(text_len=Length('text')).filter(text_len__gt=50)
    ayah = ayah_q.all()[random.randrange(ayah_q.count())]

    if mode.lower() == 'word':
        key = 'questions'
        questions = []
        ayah_words = ayah.text.split()
        q_text = ayah_words[:4]
        q_remaining = ayah_words[4:]
        for word in q_remaining:
            options = [{
                'text': word,
                'isCorrect': True,
                'selected': False,
            }]
            for other in trained_model.next_word(' '.join(q_text)):
                if other[0] in {o['text'] for o in options}:
                    continue
                options.append({
                    'text': other[0],
                    'isCorrect': False,
                    'selected': False,
                })
            for other in random.sample(q_text[:-1], max(0, 4 - len(options))):
                options.append({
                    'text': other,
                    'isCorrect': False,
                    'selected': False,
                })
            random.shuffle(options)
            questions.append({
                'text': ' '.join(q_text),
                'options': options,
            })
            q_text.append(word)
        value = questions
    elif mode.lower() == 'verse':
        key = 'options'
        next_ayah = Ayah.objects.get(id=ayah.id+1)
        options = [{
            'text': next_ayah.text,
            'isCorrect': True,
            'selected': False,
        }]
        for other in trained_model2.get_top_n(next_ayah.text, ayah_korpus, n=3, print_top=False):
            options.append({
                'text': other[1]['text'],
                'isCorrect': False,
                'selected': False,
            })
        random.shuffle(options)
        value = options
    else:
        return HttpResponseBadRequest(
            "mode must either 'verse' or 'word'"
        )

    from pprint import pprint
    pprint(value)

    return JsonResponse({
        'text': ayah.text,
        key: value,
        'mode': mode,
        'title': ayah.surah.english_name,
        'number': ayah.number,
    })
