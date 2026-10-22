from django.db import models
from django.utils.text import slugify


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Profile(TimeStamped):
    full_name = models.CharField(max_length=120)
    headline = models.CharField(max_length=200)
    bio = models.TextField()
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    location = models.CharField(max_length=120, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    resume = models.FileField(upload_to='resume/', blank=True, null=True)
    github_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    x_url = models.URLField(blank=True)
    website_url = models.URLField(blank=True)
    years_of_experience = models.PositiveIntegerField(default=0)
    is_available_for_hire = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # shudhu 1 ta Profile row thakte dibe
        if not self.pk and Profile.objects.exists():
            raise ValueError("Only one Profile is allowed.")
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        return cls.objects.first()

    def __str__(self):
        return self.full_name


class Skill(TimeStamped):
    class Category(models.TextChoices):
        FRONTEND = 'FRONTEND', 'Frontend'
        BACKEND = 'BACKEND', 'Backend'
        DATABASE = 'DATABASE', 'Database'
        DEVOPS = 'DEVOPS', 'DevOps'
        TOOLS = 'TOOLS', 'Tools'
        SOFT_SKILL = 'SOFT_SKILL', 'Soft Skill'

    name = models.CharField(max_length=60, unique=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    proficiency = models.PositiveIntegerField()  # 1-100, validation serializer e hobe
    icon = models.ImageField(upload_to='skills/', blank=True, null=True)
    display_order = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class Experience(TimeStamped):
    class EmploymentType(models.TextChoices):
        FULL_TIME = 'FULL_TIME', 'Full Time'
        PART_TIME = 'PART_TIME', 'Part Time'
        INTERNSHIP = 'INTERNSHIP', 'Internship'
        FREELANCE = 'FREELANCE', 'Freelance'
        CONTRACT = 'CONTRACT', 'Contract'

    company = models.CharField(max_length=120)
    role = models.CharField(max_length=120)
    employment_type = models.CharField(max_length=20, choices=EmploymentType.choices)
    location = models.CharField(max_length=120, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField()
    company_url = models.URLField(blank=True)
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.role} at {self.company}"


class Education(TimeStamped):
    institution = models.CharField(max_length=160)
    degree = models.CharField(max_length=120)
    field_of_study = models.CharField(max_length=120)
    start_year = models.PositiveIntegerField()
    end_year = models.PositiveIntegerField(null=True, blank=True)
    grade = models.CharField(max_length=40, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['-start_year']

    def __str__(self):
        return f"{self.degree} - {self.institution}"


class Project(TimeStamped):
    class Category(models.TextChoices):
        WEB = 'WEB', 'Web'
        MOBILE = 'MOBILE', 'Mobile'
        API = 'API', 'API'
        ML = 'ML', 'Machine Learning'
        OTHER = 'OTHER', 'Other'

    title = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    summary = models.CharField(max_length=200)
    description = models.TextField()
    cover_image = models.ImageField(upload_to='projects/')
    tech_stack = models.ManyToManyField(Skill, related_name='projects', blank=True)
    category = models.CharField(max_length=10, choices=Category.choices, default=Category.WEB)
    live_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    is_featured = models.BooleanField(default=False)
    completed_date = models.DateField(null=True, blank=True)
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['display_order', '-completed_date']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title