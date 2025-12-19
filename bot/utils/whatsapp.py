import urllib.parse

# Номера получателей WhatsApp согласно ТЗ
WHATSAPP_TESTS = "77026953357"  # +7 702 695 33 57 для тестов ПДД
WHATSAPP_SCHOOLS_INSTRUCTORS = "77788981396"  # +7 778 898 13 96 для автошкол и инструкторов (основной)
WHATSAPP_SCHOOLS_INSTRUCTORS_ALT = "77066768821"  # +7 706 676 88 21 (альтернативный, для ротации)


def build_wa_link_tests(phone: str, data: dict, category_name: str = "", lang: str = "RU") -> str:
    """Генерация WhatsApp ссылки для тестов согласно новому ТЗ (номер: +7 702 695 33 57)"""
    # Используем фиксированный номер согласно ТЗ
    owner_phone = WHATSAPP_TESTS  # +7 702 695 33 57
    if not owner_phone:
        return ""
    
    # Новый шаблон согласно ТЗ
    service_name = "Тесты по ПДД" if lang == "RU" else "ЖҚД тесттері"
    
    if lang == "KZ":
        text = (
            f"Здравствуйте!\n\n"
            f"Новая заявка с Telegram-бота.\n\n"
            f"👤 Имя: {data.get('name', '')}\n"
            f"🆔 ЖСН: {data.get('iin', '')}\n"
            f"💬 WhatsApp: {data.get('whatsapp', '')}\n"
            f"📘 Услуга: {service_name}\n"
        )
        if category_name:
            text += f"📗 Санат: {category_name}\n"
        text += f"🌐 Тіл: KZ"
    else:
        text = (
            f"Здравствуйте!\n\n"
            f"Новая заявка с Telegram-бота.\n\n"
            f"👤 Имя: {data.get('name', '')}\n"
            f"🆔 ИИН: {data.get('iin', '')}\n"
            f"💬 WhatsApp: {data.get('whatsapp', '')}\n"
            f"📘 Услуга: {service_name}\n"
        )
        if category_name:
            text += f"📗 Категория: {category_name}\n"
        text += f"🌐 Язык: RU"
    
    return f"https://wa.me/{owner_phone.replace('+', '')}?text={urllib.parse.quote(text)}"


def build_wa_link_school(detail: dict, name: str, phone: str, tariff: dict, category_name: str = "", lang: str = "RU") -> str:
    """Генерация WhatsApp ссылки с шаблоном для автошколы согласно ТЗ"""
    # Используем фиксированный номер согласно ТЗ
    owner_phone = WHATSAPP_SCHOOLS_INSTRUCTORS
    
    school_name = detail.get('name', {}).get('kz' if lang == "KZ" else 'ru', detail.get('name', {}).get('ru', ''))
    service_name = "Автошкола" if lang == "RU" else "Автошкола"
    
    # Новый шаблон согласно ТЗ
    if lang == "KZ":
        text = (
            f"Здравствуйте!\n\n"
            f"Новая заявка с Telegram-бота.\n\n"
            f"👤 Имя: {name}\n"
            f"💬 WhatsApp: {phone}\n"
            f"📘 Услуга: {service_name} — {school_name}\n"
        )
        if category_name:
            text += f"📗 Санат: {category_name}\n"
        text += f"🌐 Тіл: KZ"
    else:
        text = (
            f"Здравствуйте!\n\n"
            f"Новая заявка с Telegram-бота.\n\n"
            f"👤 Имя: {name}\n"
            f"💬 WhatsApp: {phone}\n"
            f"📘 Услуга: {service_name} — {school_name}\n"
        )
        if category_name:
            text += f"📗 Категория: {category_name}\n"
        text += f"🌐 Язык: RU"
    
    return f"https://wa.me/{owner_phone.replace('+', '')}?text={urllib.parse.quote(text)}"


def build_wa_link_instructor(instructor_detail: dict, name: str, phone: str, category_name: str = "", lang: str = "RU") -> str:
    """Генерация WhatsApp ссылки с шаблоном для инструктора согласно ТЗ"""
    # Используем фиксированный номер согласно ТЗ
    owner_phone = WHATSAPP_SCHOOLS_INSTRUCTORS
    
    instructor_name = instructor_detail.get('display_name', '')
    service_name = "Инструктор" if lang == "RU" else "Нұсқаушы"
    
    # Новый шаблон согласно ТЗ
    if lang == "KZ":
        text = (
            f"Здравствуйте!\n\n"
            f"Новая заявка с Telegram-бота.\n\n"
            f"👤 Имя: {name}\n"
            f"💬 WhatsApp: {phone}\n"
            f"📘 Услуга: {service_name} — {instructor_name}\n"
        )
        if category_name:
            text += f"📗 Санат: {category_name}\n"
        text += f"🌐 Тіл: KZ"
    else:
        text = (
            f"Здравствуйте!\n\n"
            f"Новая заявка с Telegram-бота.\n\n"
            f"👤 Имя: {name}\n"
            f"💬 WhatsApp: {phone}\n"
            f"📘 Услуга: {service_name} — {instructor_name}\n"
        )
        if category_name:
            text += f"📗 Категория: {category_name}\n"
        text += f"🌐 Язык: RU"
    
    return f"https://wa.me/{owner_phone.replace('+', '')}?text={urllib.parse.quote(text)}"

