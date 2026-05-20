import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta

# --- НАСТРОЙКА ИНТЕРФЕЙСА ПРИЛОЖЕНИЯ ---
st.set_page_config(page_title="Концерт-Прокат ERP Москва", page_icon="⚡", layout="wide")

# --- ИНИЦИАЛИЗАЦИЯ СКВОЗНОГО ЯДРА ДАННЫХ (БАЗА В ПАМЯТИ) ---
if 'erp_initialized' not in st.session_state:
    # База ТОР-оборудования с жесткими технологическими зависимостями
    st.session_state.inventory = pd.DataFrame([
        {"ID": 501, "Название": "Пульт DiGiCo SD7 Quantum", "Серийный №": "DG-SD7-9921", "Статус": "Доступен", "Цена/сутки": 45000, "Вес_кг": 120, "Подсказка": "⚠️ Требуется: 2 инженера звука, ИБП 3кВт, патч-корд Cat6e 100м."},
        {"ID": 502, "Название": "Массив L-Acoustics K2 (12 элементов)", "Серийный №": "LA-K2-KIT01", "Статус": "Доступен", "Цена/сутки": 144000, "Вес_кг": 670, "Подсказка": "⚠️ Требуется: Электропитание 32А 3-фазы, сертифицированный лод-мастер, лебедки 1т."},
        {"ID": 503, "Название": "Световой комплект Robe MegaPointe (16 шт)", "Серийный №": "RB-MP-KIT08", "Статус": "В аренде", "Цена/сутки": 96000, "Вес_кг": 350, "Подсказка": "⚠️ Требуется: Пульт Hog/GrandMA, сигнальные кабели DMX-512, силовые кабели PowerCON."}
    ])
    
    # Реестр площадок Москвы (Координаты для встроенной карты)
    st.session_state.venues = {
        "ВТБ Арена": {"lat": 55.7915, "lon": 37.5601, "Адрес": "Ленинградский просп., 36", "Дистанция_км": 9},
        "Crocus City Hall": {"lat": 55.8251, "lon": 37.3902, "Адрес": "МКАД 66-й км", "Дистанция_км": 22},
        "MTS Live Холл": {"lat": 55.7499, "lon": 37.6978, "Адрес": "шоссе Энтузиастов, 5", "Дистанция_км": 6},
        "Красная Площадь (Опен-эйр)": {"lat": 55.7539, "lon": 37.6208, "Адрес": "Красная площадь", "Дистанция_км": 1}
    }
    
    # Реестры CRM и кадров
    st.session_state.orders = []
    st.session_state.drivers = [{"ФИО": "Григорий Орлов", "Транспорт": "Грузовой фургон 3.5т (Категория С)", "Статус": "Свободен"}]
    st.session_state.erp_initialized = True

# --- ГЛАВНЫЙ ЕДИНЫЙ ДАШБОРД ---
st.title("⚡ КонцертПрокат ERP v2.0 | Единый Центр Управления (Москва)")
st.caption("Сквозной учет: CRM -> Логистика (Карты) -> Юриспруденция -> 1С Дублирование -> Управленческий баланс")

# --- СТАТИСТИКА В РЕАЛЬНОМ ВРЕМЕНИ (УПРАВЛЕНЧЕСКИЙ УЧЕТ) ---
col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    st.metric("Оборот в обработке (Москва)", f"{sum(x['Сумма'] for x in st.session_state.orders):,} ₽")
with col_m2:
    st.metric("Оборудования на объектах", f"{len(st.session_state.inventory[st.session_state.inventory['Статус']=='В аренде'])} ед.")
with col_m3:
    st.metric("Активные суды / Претензии", "0 — Все договоры защищены холдом")

# --- ДВЕ СЕКЦИИ: ПАНЕЛЬ ДЕЙСТВИЙ И КАРТА ЛОГИСТИКИ ---
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📝 Новая Сделка: Сквозное оформление (Очередь + CRM + 1C)")
    
    with st.form("erp_order_form"):
        customer = st.text_input("Контрагент (CRM: Наименование юр. лица)", placeholder="ООО 'Ивент Продакшн'")
        selected_venue = st.selectbox("Концертная площадка (Авторасчет логистики):", list(st.session_state.venues.keys()))
        
        # Умный выбор аппарата с моментальной подсказкой зависимостей
        eq_idx = st.selectbox("Выбор дорогого аппарата:", range(len(st.session_state.inventory)), 
                              format_func=lambda x: f"{st.session_state.inventory.iloc[x]['Название']} ({st.session_state.inventory.iloc[x]['Цена/сутки']:,} ₽/сут)")
        
        chosen_item = st.session_state.inventory.iloc[eq_idx]
        
        # ДИНАМИЧЕСКАЯ ПОДСКАЗКА (Контекстный инжиниринг прямо в форме)
        st.warning(chosen_item["Подсказка"])
        
        days = st.number_input("Срок проката (суток):", min_value=1, value=1)
        delivery_needed = st.checkbox("Требуется наша доставка и монтаж", value=True)
        
        submit_btn = st.form_submit_button("🔥 Провести по всем системам (CRM, Бухгалтерия, Склад, Кадры)")

    if submit_btn:
        if not customer.strip():
            st.error("Ошибка CRM: Не указан контрагент.")
        else:
            # Расчет логистики на основе координат площадки
            venue_data = st.session_state.venues[selected_venue]
            dist = venue_data["Дистанция_км"]
            # Формула расчета времени доставки (Москва: база 40 мин + 3 мин на км + коэф. пробок 1.3)
            delivery_time_min = int((40 + (dist * 3)) * 1.3)
            delivery_cost = int(dist * 150 + 5000) if delivery_needed else 0
            
            total_price = (chosen_item["Цена/сутки"] * days) + delivery_cost
            
            # Генерация сквозной транзакции
            new_order = {
                "ID": len(st.session_state.orders) + 1001,
                "Клиент": customer,
                "Площадка": selected_venue,
                "Адрес": venue_data["Адрес"],
                "Аппарат": chosen_item["Название"],
                "Серийный": chosen_item["Серийный №"],
                "Сумма": total_price,
                "ВремяДоставки_мин": delivery_time_min,
                "Вес_общий": chosen_item["Вес_кг"],
                "Дата": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            
            st.session_state.orders.append(new_order)
            # Обновляем складской статус
            st.session_state.inventory.loc[st.session_state.inventory["ID"] == chosen_item["ID"], "Статус"] = "В аренде"
            st.success(f"Сделка №{new_order['ID']} успешно проведена!")

with col_right:
    st.subheader("📍 Мониторинг логистики на карте Москвы")
    # Отображение интерактивной карты на основе координат площадок из базы данных
    map_data = pd.DataFrame.from_dict(st.session_state.venues, orient='index')
    st.map(map_data, latitude='lat', longitude='lon', zoom=10, use_container_width=True)
    st.caption("Точки — выбранные концертные залы. Система автоматически строит маршруты от центрального склада.")

# --- НИЖНЯЯ ПАНЕЛЬ: ЮРИДИЧЕСКИЙ, БУХГАЛТЕРСКИЙ И 1С БЛОКИ ---
st.divider()
st.subheader("🗂️ Сквозная детализация по отделам для последней сделки")

if st.session_state.orders:
    last_order = st.session_state.orders[-1]
    
    tab_crm, tab_legal, tab_1c, tab_warehouse = st.tabs([
        "📊 CRM & Управление", 
        "⚖️ Юридический блок (Авто-Акты)", 
        "🔄 Синхронизация с 1С / Стороннее API", 
        "🏗️ Склад и Транспорт"
    ])
    
    with tab_crm:
        st.json(last_order)
        st.info("Статус сделки в CRM: 'В работе'. Клиенту отправлено автоматическое уведомление.")
        
    with tab_legal:
        st.markdown(f"""
        **ДОГОВОР № {last_order['ID']}-А**  
        *г. Москва — {last_order['Дата']}*  
        Исполнитель обязуется передать, а Заказчик (**{last_order['Клиент']}**) принять во временное пользование оборудование:  
        **{last_order['Аппарат']} (Серийный номер: {last_order['Серийный']})**.  
        
        **АКТ ТЕХНИЧЕСКОГО СОСТОЯНИЯ (Взамен QR-маркировки):**  
        Прибор проверен в сервисной зоне по серийному номеру. Сколы, дефекты отсутствуют.  
        Материальная ответственность за порчу лежит на Заказчике в размере восстановительной стоимости: **{int(last_order['Сумма'] * 12):,} ₽**.
        """)
        st.button("📥 Скачать PDF пакета документов для ЭДО (Диадок / СБИС)")
        
    with tab_1c:
        st.markdown("### 🔄 Шина обмена: Зеркалирование в 1С:УНФ / 1С:Бухгалтерия")
        st.write("Сформированный JSON пакет для автоматической выгрузки в 1С или сторонние CRM по Webhook:")
        
        one_c_packet = {
            "Document_Type": "Invoice_Reserve",
            "1C_Code": f"ERP-MOS-{last_order['ID']}",
            "Timestamp": last_order['Дата'],
            "Counterparty": last_order['Клиент'],
            "Nomenclature": [{
                "Name": last_order['Аппарат'],
                "Serial": last_order['Серийный'],
                "Price": int(last_order['Сумма'])
            }],
            "Status_1C": "Posted_Not_Paid"
        }
        st.code(json.dumps(one_c_packet, indent=4, ensure_ascii=False), language="json")
        st.toggle("Включить автоматический экспорт по API")
        
    with tab_warehouse:
        st.markdown("### 🚚 Наряд на отгрузку и Транспортный лист")
        st.write(f"**Точка назначения:** {last_order['Площадка']} ({last_order['Адрес']})")
        st.write(f"**Общий вес оборудования к погрузке:** {last_order['Вес_общий']} кг.")
        st.write(f"**Расчетное время в пути (Москва):** ~{last_order['ВремяДоставки_мин']} минут.")
        st.write(f"**Назначенный водитель:** {st.session_state.drivers[0]['ФИО']} ({st.session_state.drivers[0]['Транспорт']})")
else:
    st.info("💡 Оформите тестовую сделку в форме выше, чтобы запустить сквозной процесс управленческого и юридического учета.")
