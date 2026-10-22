import os
from datetime import date

from rest_framework import serializers

from .models import Education, Experience, Profile, Project, Skill

MAX_IMAGE_SIZE = 2 * 1024 * 1024
MAX_RESUME_SIZE = 5 * 1024 * 1024
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp')


def validate_image(file):
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in IMAGE_EXTENSIONS:
        raise serializers.ValidationError(
            'Only .jpg, .jpeg, .png and .webp images are allowed.'
        )
    if file.size > MAX_IMAGE_SIZE:
        raise serializers.ValidationError('Image size must be 2 MB or less.')
    return file


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def validate_avatar(self, value):
        if value:
            validate_image(value)
        return value

    def validate_resume(self, value):
        if value:
            if not value.name.lower().endswith('.pdf'):
                raise serializers.ValidationError('Resume must be a PDF file.')
            if value.size > MAX_RESUME_SIZE:
                raise serializers.ValidationError('Resume size must be 5 MB or less.')
        return value


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def validate_proficiency(self, value):
        if not 1 <= value <= 100:
            raise serializers.ValidationError('Proficiency must be between 1 and 100.')
        return value

    def validate_icon(self, value):
        if value:
            validate_image(value)
        return value


class ExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experience
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def validate_start_date(self, value):
        if value > date.today():
            raise serializers.ValidationError('Start date cannot be in the future.')
        return value

    def validate(self, attrs):
        inst = self.instance

        def get(name, default=None):
            if name in attrs:
                return attrs[name]
            return getattr(inst, name, default) if inst else default

        is_current = get('is_current', False)
        start = get('start_date')
        end = get('end_date')

        if is_current:
            if end:
                raise serializers.ValidationError(
                    {'end_date': 'End date must be empty for a current position.'}
                )
        else:
            if not end:
                raise serializers.ValidationError(
                    {'end_date': 'End date is required unless this is your current position.'}
                )
            if start and end <= start:
                raise serializers.ValidationError(
                    {'end_date': 'End date must be after start date.'}
                )
        return attrs


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def validate(self, attrs):
        inst = self.instance
        start = attrs.get('start_year', getattr(inst, 'start_year', None))
        end = attrs.get('end_year', getattr(inst, 'end_year', None))
        if start and end and end < start:
            raise serializers.ValidationError(
                {'end_year': 'End year cannot be before start year.'}
            )
        return attrs


class SkillMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ('id', 'name', 'category')


class ProjectSerializer(serializers.ModelSerializer):
    tech_stack = SkillMiniSerializer(many=True, read_only=True)
    tech_stack_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Skill.objects.all(),
        source='tech_stack',
        write_only=True,
        required=False,
    )

    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = ('slug', 'created_at', 'updated_at')

    def validate_title(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError('Title must be at least 3 characters.')
        return value

    def validate_cover_image(self, value):
        if value:
            validate_image(value)
        return value

    def validate(self, attrs):
        inst = self.instance

        def get(name):
            if name in attrs:
                return attrs[name]
            return getattr(inst, name, '') if inst else ''

        if not get('live_url') and not get('github_url'):
            raise serializers.ValidationError(
                {'live_url': 'Provide at least one of live_url or github_url.'}
            )
        return attrs