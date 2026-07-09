---
layout: default
title: Galleri
permalink: /gallery/
---

# Galleri

En liten samling av bilder fra reisen, gruppert etter hvilken uke de hører til.

<!-- Gallery filter UI -->
<link rel="stylesheet" href="{{ '/assets/css/gallery-filter.css' | relative_url }}">
<div class="gallery-controls">
  <label>Land: <select id="gf-country"><option value="">Alle</option></select></label>
  <label>By: <select id="gf-city"><option value="">Alle</option></select></label>
  <label>Uke: <select id="gf-week"><option value="">Alle</option></select></label>
  <label>Sorter etter: <select id="gf-sort"><option value="original">Original</option><option value="caption">Bildetekst</option><option value="city">By</option><option value="country">Land</option></select></label>
</div>
<script src="{{ '/assets/js/gallery-filter.js' | relative_url }}" defer></script>

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
 
