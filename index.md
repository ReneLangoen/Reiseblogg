---
layout: default
title: Hjem
---

<section class="post-list">

  {% for post in site.posts limit:6 %}
    <article class="post-card">
      <a class="post-card-link" href="{{ post.url | relative_url }}">
        {% assign hero_id = post.hero_image | default: post.images.first.id %}
        {% assign hero = post.images | where: "id", hero_id | first %}
        {% if hero %}
          <div class="post-card-image-wrap">
            <img class="post-card-image" src="{{ hero.src | relative_url }}" alt="{{ hero.caption | default: post.title }}">
          </div>
        {% elsif post.image %}
          <div class="post-card-image-wrap">
            <img class="post-card-image" src="{{ post.image | relative_url }}" alt="{{ post.image_alt | default: post.title }}">
          </div>
        {% else %}
          <div class="post-card-image-wrap placeholder"></div>
        {% endif %}
        <div class="post-card-content">
          <p class="meta">{{ post.date | date: "%b %-d, %Y" }}{% if post.location %} · {{ post.location }}{% endif %}</p>
          <h3>{{ post.title }}</h3>
          <p>{{ post.description | default: post.excerpt | strip_html | truncate: 150 }}</p>
          <div class="tags">
            {% for tag in post.tags %}<span>{{ tag }}</span>{% endfor %}
          </div>
        </div>
      </a>
    </article>
  {% endfor %}
</section>
