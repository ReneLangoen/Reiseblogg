---
layout: default
title: Hjem
---

<section class="post-list">

  {% for post in site.posts limit:6 %}
    <article class="post-card">
      <a class="post-card-link" href="{{ post.url | relative_url }}">
        {% if post.image %}
          <img class="post-card-image" src="{{ post.image | relative_url }}" alt="{{ post.image_alt | default: post.title }}">
        {% else %}
          <div class="post-card-image placeholder"></div>
        {% endif %}
        <div class="post-card-content">
          <p class="meta">{{ post.date | date: "%b %-d, %Y" }}{% if post.location %} · {{ post.location }}{% endif %}</p>
          <h3>{{ post.title }}</h3>
          <p>{{ post.description | default: post.excerpt | strip_html | truncate: 150 }}</p>
          <div class="tags">
            {% for tag in post.tags limit:4 %}<span>{{ tag }}</span>{% endfor %}
          </div>
        </div>
      </a>
    </article>
  {% endfor %}
</section>
