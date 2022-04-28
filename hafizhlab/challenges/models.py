import operator

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class Challenge(models.Model):
    class Mode(models.TextChoices):
        AYAH_BASED = 'ayah'
        WORD_BASED = 'word'

    SCOPE_CHOICES = operator.or_(
        models.Q(app_label='quran', model='juz'),
        models.Q(app_label='quran', model='surah'),
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    is_public = models.BooleanField(default=False)
    mode = models.CharField(max_length=4, choices=Mode.choices)

    scope_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        limit_choices_to=SCOPE_CHOICES,
    )
    scope_id = models.PositiveSmallIntegerField()
    scope = GenericForeignKey('scope_type', 'scope_id')


class Question(models.Model):
    NUMBER_OF_OPTIONS = 4

    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    ayah = models.ForeignKey('quran.Ayah', on_delete=models.CASCADE)
    options = models.JSONField()

    def clean(self):
        self._check_ayah_in_challenge_scope()
        self._check_answer_exist()
        self._check_option_format()

    def _check_ayah_in_challenge_scope(self):
        if not self.challenge.scope.ayah_set.filter(pk=self.ayah.pk).exists():
            raise ValidationError(_("Question's ayah should be in the scope"))

    def _check_answer_exist(self):
        error_msg = _('The answer should exist in options')
        if self.challenge.mode == Challenge.Mode.AYAH_BASED:
            if self.ayah_id not in self.options:
                raise ValidationError(error_msg)

        elif self.challenge.mode == Challenge.Mode.WORD_BASED:
            if not all(word in option for word, option in zip(self.ayah.text.split(), self.options)):
                raise ValidationError(error_msg)

    def _check_option_format(self):
        option_type = {
            Challenge.Mode.AYAH_BASED: int,
            Challenge.Mode.WORD_BASED: str,
        }

        def check_format(opt):
            return operator.and_(
                len(opt) == self.NUMBER_OF_OPTIONS,
                all(isinstance(x, option_type[self.challenge.mode])
                    for x in opt)
            )

        if self.challenge.mode == Challenge.Mode.AYAH_BASED:
            if not check_format(self.options):
                raise ValidationError(_(
                    "Question's options for ayah based challenge should be in "
                    "the format of [<ayah_id>, <ayah_id>, <ayah_id>, <ayah_id>]."
                ))
        elif self.challenge.mode == Challenge.Mode.WORD_BASED:
            if not all(check_format(o) for o in self.options):
                raise ValidationError(_(
                    "Question's options for word based challenge should be in "
                    "the format of [['opt1', 'opt2', 'opt3', 'opt4'], "
                    "['opt5', 'opt6', 'opt7', 'opt8'], ...]."
                ))
