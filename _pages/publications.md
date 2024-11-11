---
layout: archive
title: "Research"
permalink: /research/
author_profile: true
---

{% if author.googlescholar %}
  You can also find my articles on <u><a href="{{author.googlescholar}}">my Google Scholar profile</a>.</u>
{% endif %}

{% include base_path %}

---

## Working Papers
<ul>
{% for post in site.data.working-papers %}
  {% include archive-single-publication.html %}
{% endfor %}
</ul>

## Journal Articles
<!-- **Under Submission** -->
<ul>
{% for post in site.data.journal-submissions %}
  {% include archive-single-publication.html %}
{% endfor %}
</ul>

<!-- **Published** -->
<ul>
{% for post in site.data.journal %}
  {% include archive-single-publication.html %}
{% endfor %}
</ul>



## Conference Publications
<ul>
{% for post in site.data.publications %}
  {% include archive-single-publication.html %}
{% endfor %}
</ul>

## Unpublished Manuscripts

<ul>
{% for post in site.data.unpublished %}
  {% include archive-single-publication.html %}
{% endfor %}
</ul>