---
layout: archive
title: "Research"
permalink: /research/
author_profile: false
hide_title: true
---

{% include base_path %}

<h3 class="publication-year">Working Papers</h3>
<ul>
{% for post in site.data.working-papers %}
  {% include archive-single-publication.html %}
{% endfor %}
</ul>

{% assign current_year = "" %}
{% for post in site.data.papers %}
  {% if post.year != current_year %}
    {% if current_year != "" %}
</ul>
    {% endif %}
    {% assign current_year = post.year %}
<h3 class="publication-year">{{ current_year }}</h3>
<ul>
  {% endif %}
  {% include archive-single-publication.html %}
{% endfor %}
{% if current_year != "" %}
</ul>
{% endif %}