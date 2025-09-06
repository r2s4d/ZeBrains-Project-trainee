# 🚀 GPTunnel Setup Guide для AI News Assistant

## **📋 Что такое GPTunnel?**

**GPTunnel** - это сервис, который создает прокси-туннель для обхода географических ограничений OpenAI API. Это позволяет использовать OpenAI API из России и других заблокированных регионов.

---

## **🔧 Способы подключения GPTunnel:**

### **Вариант 1: Через переменные окружения (Рекомендуется)**

1. **Зарегистрируйтесь на GPTunnel:**
   - Перейдите на [gptunnel.com](https://gptunnel.com)
   - Создайте аккаунт
   - Получите API ключ и настройки прокси

2. **Добавьте в ваш `.env` файл:**
```bash
# OpenAI API ключ
OPENAI_API_KEY=your_openai_api_key_here

# GPTunnel настройки
GPTUNNEL_PROXY_URL=http://your_proxy_url:port
GPTUNNEL_BASE_URL=https://api.openai.com
```

3. **Пример реальных значений:**
```bash
OPENAI_API_KEY=sk-1234567890abcdef...
GPTUNNEL_PROXY_URL=http://proxy.gptunnel.com:8080
GPTUNNEL_BASE_URL=https://api.openai.com
```

### **Вариант 2: Через HTTP/HTTPS прокси**

Если GPTunnel предоставляет HTTP прокси:

```bash
GPTUNNEL_PROXY_URL=http://username:password@proxy.gptunnel.com:8080
```

---

## **🧪 Тестирование подключения:**

### **Команда для проверки статуса:**
```bash
python3 -c "
import os
from src.services.gptunnel_service import GPTunnelService

service = GPTunnelService()
print('GPTunnel Status:', service.get_status())
"
```

### **Ожидаемый результат:**
```
✅ GPTunnel доступен и будет использован
GPTunnel Status: {
    'service': 'GPTunnelService',
    'gptunnel_available': True,
    'proxy_url': 'http://proxy.gptunnel.com:8080',
    'base_url': 'https://api.openai.com',
    'api_key_set': True
}
```

---

## **🔍 Как это работает в нашем проекте:**

1. **Автоматическое определение:** Система автоматически определяет доступность GPTunnel
2. **Приоритет GPTunnel:** Если GPTunnel доступен, используется он
3. **Fallback на OpenAI:** Если GPTunnel недоступен, используется прямой доступ
4. **Логирование:** Все действия логируются для отладки

---

## **⚠️ Возможные проблемы и решения:**

### **Проблема: "GPTunnel недоступен"**
**Решение:** Проверьте правильность URL в `GPTUNNEL_PROXY_URL`

### **Проблема: "Ошибка подключения к прокси"**
**Решение:** Убедитесь, что прокси-сервер работает и доступен

### **Проблема: "API ключ не работает"**
**Решение:** Проверьте правильность `OPENAI_API_KEY`

---

## **📱 Команды бота для мониторинга:**

После настройки вы можете использовать команду `/gptunnel_status` для проверки статуса GPTunnel.

---

## **🚀 Преимущества GPTunnel:**

- ✅ **Обход блокировки:** Работает из России и других заблокированных регионов
- ✅ **Автоматическое переключение:** Система сама выбирает лучший способ доступа
- ✅ **Безопасность:** Ваши API ключи остаются безопасными
- ✅ **Надежность:** Высокая доступность и стабильность

---

## **💡 Альтернативы GPTunnel:**

Если GPTunnel не подходит, можно рассмотреть:
- **VPN сервисы** (NordVPN, ExpressVPN)
- **Другие прокси-сервисы** (Bright Data, SmartProxy)
- **Локальные решения** (Ollama, локальные модели)

---

## **📞 Поддержка:**

При возникновении проблем:
1. Проверьте логи бота
2. Убедитесь в правильности настроек
3. Проверьте доступность прокси-сервера
4. Обратитесь в поддержку GPTunnel
