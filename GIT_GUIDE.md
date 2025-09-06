# 📚 Руководство по Git для AI News Assistant Bot

## 🚀 Быстрый старт с Git

### 1. Инициализация репозитория

```bash
# Инициализация Git репозитория
git init

# Добавление всех файлов
git add .

# Первый коммит
git commit -m "Initial commit: AI News Assistant Bot v1.0"
```

### 2. Создание ветки для разработки

```bash
# Создание и переключение на ветку разработки
git checkout -b development

# Или создание ветки с другим именем
git checkout -b feature/ai-integration
```

### 3. Подключение к GitHub

```bash
# Добавление удаленного репозитория
git remote add origin https://github.com/your-username/ai_news_assistant.git

# Отправка кода на GitHub
git push -u origin main
```

## 📋 Основные команды Git

### Работа с файлами
```bash
# Проверка статуса
git status

# Добавление файлов
git add .                    # Все файлы
git add README.md           # Конкретный файл
git add src/                # Папка

# Коммит изменений
git commit -m "Описание изменений"
git commit -am "Быстрый коммит"  # Добавить и закоммитить
```

### Работа с ветками
```bash
# Просмотр веток
git branch                  # Локальные ветки
git branch -a              # Все ветки

# Создание ветки
git branch feature-name
git checkout feature-name

# Переключение между ветками
git checkout main
git checkout development

# Слияние веток
git checkout main
git merge development
```

### Работа с удаленным репозиторием
```bash
# Получение изменений
git pull origin main

# Отправка изменений
git push origin main
git push origin feature-name

# Клонирование репозитория
git clone https://github.com/username/repository.git
```

## 🔄 Workflow для проекта

### 1. Ежедневная работа

```bash
# Начало работы
git pull origin main

# Создание ветки для задачи
git checkout -b feature/new-feature

# Работа с кодом...
# Добавление изменений
git add .
git commit -m "Add new feature: description"

# Отправка на GitHub
git push origin feature/new-feature
```

### 2. Создание Pull Request

1. Перейдите на GitHub
2. Нажмите "Compare & pull request"
3. Заполните описание изменений
4. Назначьте ревьюера (если есть)
5. Создайте Pull Request

### 3. Слияние изменений

```bash
# После одобрения PR
git checkout main
git pull origin main
git branch -d feature/new-feature  # Удаление локальной ветки
```

## 📝 Правила коммитов

### Формат сообщений
```
тип(область): краткое описание

Подробное описание изменений (если нужно)

Closes #123  # Если закрывает issue
```

### Типы коммитов
- `feat`: новая функциональность
- `fix`: исправление бага
- `docs`: изменения в документации
- `style`: форматирование кода
- `refactor`: рефакторинг
- `test`: добавление тестов
- `chore`: технические изменения

### Примеры
```bash
git commit -m "feat(bot): add morning digest command"
git commit -m "fix(ai): resolve proxy API timeout issue"
git commit -m "docs(readme): update installation instructions"
git commit -m "refactor(services): clean up unused code"
```

## 🏷️ Теги и релизы

### Создание тега
```bash
# Создание аннотированного тега
git tag -a v1.0.0 -m "Release version 1.0.0"

# Отправка тега на GitHub
git push origin v1.0.0
```

### Создание релиза на GitHub
1. Перейдите в "Releases"
2. Нажмите "Create a new release"
3. Выберите тег
4. Заполните описание
5. Прикрепите файлы (если нужно)

## 🔧 Полезные команды

### Просмотр истории
```bash
# Краткая история
git log --oneline

# Подробная история
git log --graph --pretty=format:'%h -%d %s (%cr) <%an>'

# История файла
git log --follow README.md
```

### Отмена изменений
```bash
# Отмена изменений в файле
git checkout -- filename

# Отмена последнего коммита
git reset --soft HEAD~1

# Отмена всех изменений
git reset --hard HEAD
```

### Работа с .gitignore
```bash
# Проверка игнорируемых файлов
git check-ignore -v filename

# Принудительное добавление игнорируемого файла
git add -f filename
```

## 🚨 Решение проблем

### Конфликты слияния
```bash
# Просмотр конфликтов
git status

# Решение конфликтов в файлах
# Затем:
git add resolved-file
git commit -m "Resolve merge conflict"
```

### Отмена слияния
```bash
git merge --abort
```

### Восстановление удаленных файлов
```bash
# Просмотр удаленных файлов
git log --diff-filter=D --summary

# Восстановление файла
git checkout HEAD~1 -- filename
```

## 📚 Дополнительные ресурсы

- [Официальная документация Git](https://git-scm.com/doc)
- [GitHub Guides](https://guides.github.com/)
- [Atlassian Git Tutorial](https://www.atlassian.com/git/tutorials)
- [Git Flow](https://nvie.com/posts/a-successful-git-branching-model/)

---

*Это руководство поможет вам эффективно работать с Git в проекте AI News Assistant Bot.*
