// Автокомплит тегов для админки Django
(function() {
    'use strict';
    
    document.addEventListener('DOMContentLoaded', function() {
        const tagsInput = document.getElementById('tags-input');
        if (!tagsInput) return;
        
        const autocompleteResults = document.createElement('div');
        autocompleteResults.id = 'tag-autocomplete-results';
        autocompleteResults.className = 'tag-autocomplete-results';
        autocompleteResults.style.cssText = 'position: absolute; background: white; border: 1px solid #ccc; border-radius: 4px; max-height: 200px; overflow-y: auto; z-index: 1000; width: 100%; margin-top: 2px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); display: none;';
        
        // Вставляем контейнер для результатов после поля ввода
        tagsInput.parentNode.appendChild(autocompleteResults);
        
        let selectedTags = new Set();
        
        // Инициализируем выбранные теги из существующих
        if (tagsInput.value) {
            const existingTags = tagsInput.value.split(',').map(t => t.trim()).filter(t => t);
            existingTags.forEach(tag => selectedTags.add(tag));
        }
        
        function addTag(tagName) {
            if (!selectedTags.has(tagName)) {
                selectedTags.add(tagName);
                updateTagsInput();
            }
            autocompleteResults.style.display = 'none';
            tagsInput.value = '';
        }
        
        function updateTagsInput() {
            tagsInput.value = Array.from(selectedTags).join(', ');
        }
        
        // Обработка ввода с задержкой для автокомплита
        let autocompleteTimeout;
        tagsInput.addEventListener('input', function() {
            clearTimeout(autocompleteTimeout);
            const value = this.value.trim();
            
            // Если пользователь вводит запятую или Enter, добавляем тег
            if (value.includes(',')) {
                const tags = value.split(',').map(t => t.trim()).filter(t => t);
                tags.forEach(tag => {
                    if (tag && !selectedTags.has(tag)) {
                        selectedTags.add(tag);
                    }
                });
                updateTagsInput();
                this.value = '';
                autocompleteResults.style.display = 'none';
                return;
            }
            
            // Показываем автокомплит только если введено больше 1 символа
            if (value.length > 1) {
                autocompleteTimeout = setTimeout(function() {
                    fetch('/tags/autocomplete/?q=' + encodeURIComponent(value))
                        .then(response => response.text())
                        .then(html => {
                            if (html.trim()) {
                                autocompleteResults.innerHTML = html;
                                autocompleteResults.style.display = 'block';
                                
                                // Добавляем обработчики кликов для элементов автокомплита
                                const items = autocompleteResults.querySelectorAll('.tag-autocomplete-item');
                                items.forEach(item => {
                                    item.addEventListener('click', function() {
                                        const tagName = this.getAttribute('data-tag-name');
                                        if (tagName) {
                                            addTag(tagName);
                                        }
                                    });
                                });
                            } else {
                                autocompleteResults.style.display = 'none';
                            }
                        })
                        .catch(function() {
                            autocompleteResults.style.display = 'none';
                        });
                }, 300);
            } else {
                autocompleteResults.style.display = 'none';
            }
        });
        
        // Обработка нажатия Enter или запятой
        tagsInput.addEventListener('keydown', function(e) {
            if (e.key === ',' || e.key === 'Enter') {
                e.preventDefault();
                const value = this.value.trim();
                if (value && !value.includes(',')) {
                    if (!selectedTags.has(value)) {
                        selectedTags.add(value);
                        updateTagsInput();
                    }
                    this.value = '';
                    autocompleteResults.style.display = 'none';
                }
            } else if (e.key === 'Escape') {
                autocompleteResults.style.display = 'none';
            }
        });
        
        // Скрываем автокомплит при клике вне поля
        document.addEventListener('click', function(e) {
            if (!tagsInput.contains(e.target) && !autocompleteResults.contains(e.target)) {
                autocompleteResults.style.display = 'none';
            }
        });
        
        // Предотвращаем скрытие при клике на сам автокомплит
        autocompleteResults.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    });
})();











