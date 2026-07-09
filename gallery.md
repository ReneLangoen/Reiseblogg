---
layout: default
title: Galleri
permalink: /gallery/
---

# Galleri

En liten samling av bilder fra reisen, gruppert etter hvilken uke de hører til.

{% assign posts_with_gallery = site.posts | where_exp: "post", "post.gallery_images" %}
{% for post in posts_with_gallery %}
<section class="gallery-week">
  <h2>{{ post.week_label | default: post.title }}</h2>
  <div class="gallery-grid">
    {% for photo in post.gallery_images %}
    <figure class="gallery-card">
      <img src="{{ photo.image | relative_url }}" alt="{{ photo.caption | default: post.title }}" loading="lazy"
           data-city="{{ photo.city | default: post.location | split: "," | first | strip }}"
           data-country="{{ photo.country | default: post.location | split: "," | last | strip }}"
           data-week="{{ post.week_label | default: post.title }}">
      <figcaption>{{ photo.caption }}</figcaption>
    </figure>
    {% endfor %}
  </div>
</section>
{% endfor %}

<!-- Lightbox assets -->
<link rel="stylesheet" href="{{ '/assets/css/lightbox.css' | relative_url }}">
<script src="{{ '/assets/js/lightbox.js' | relative_url }}" defer></script>
