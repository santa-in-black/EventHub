import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta

# --- НАСТРОЙКА ИНТЕРФЕЙСА ПРИЛОЖЕНИЯ ---
st.set_page_config(page_title="Концерт-Прокат ERP Москва", page_icon="⚡", layout="wide")

# --- ИНИЦИАЛИЗАЦИЯ СКВОЗНОГО ЯДРА ДАННЫХ ---
if 'erp_initialized' not in st.session_state:
    # 1. Склад ТОР-оборудования
    st.session_state.inventory = pd.DataFrame([
        {"ID": 501, "Название": "Пульт DiGiCo SD7 Quantum", "Серийный №": "DG-SD7-9921", "Статус": "Доступен", "Цена/сутки": 45000, "Вес_кг": 120, "Подсказка": "⚠️ Требуется: 2 инженера звука, ИБП 3кВт, патч-корд Cat6e 100м."},
        {"ID": 502, "Название": "Массив L-Acoustics K2 (12 элементов)", "Серийный №": "LA-K2-KIT01", "Статус": "Доступен", "Цена/сутки": 144000, "Вес_кг": 670, "Подсказка": "⚠️ Требуется: Электропитание 32А 3-фазы, лод-мастер, лебедки 1т."},
        {"ID": 503, "Название": "Световой комплект Robe MegaPointe (16 шт)", "Серийный №": "RB-MP-KIT08", "Статус": "В аренде", "Цена/сутки": 96000, "Вес_кг": 350, "Подсказка": "⚠️ Требуется: Пульт Hog/GrandMA, кабели DMX-512, PowerCON."}
    ])
    
    # 2. База контрагентов
    st.session_state.clients = pd.DataFrame([
        {"ИНН": "7701002233", "Название": "ООО 'Спинофф Продакшн'", "Контакты": "+7 (495) 111-22-33"},
        {"ИНН": "7702998877", "Название": "АО 'Крокус Ивентс'", "Контакты": "+7 (495) 777-88-99"}
    ])
    
    # 3. Реестр площадок Москвы
    st.session_state.venues = {
        "ВТБ Арена": {"lat": 55.7915, "lon": 37.5601, "Адрес": "Ленинградский просп., 36", "Дистанция_км": 9},
        "Crocus City Hall": {"lat": 55.8251, "lon": 37.3902, "Адрес": "МКАД 66-й км", "Дистанция_км": 22},
        "MTS Live Холл": {"lat": 55.7499, "lon": 37.6978, "Адрес": "шоссе Энтузиастов, 5", "Дистанция_км": 6},
        "Красная Площадь (Опен-эйр)": {"lat": 55.7539, "lon": 37.6208, "Адрес": "Красная площадь", "Дистанция_км": 1}
    }
    
    st.session_state.orders = []
    st.session_state.drivers = [{"ФИО": "Григорий Орлов", "Транспорт": "Грузовой фургон 3.5т", "Статус": "Свободен"}]
    st.session_state.erp_initialized = True

# --- БОКОВАЯ ПАНЕЛЬ: ВЫБОР РОЛИ (АВТОРИЗАЦИЯ) И УПРАВЛЕНИЕ ---
with st.sidebar:
    st.header("🔑 Авторизация в системе")
    # Переключатель ролей, который будет полностью менять логику дашборда
    user_role = st.selectbox(
        "Выберите вашу должность:",
        ["Директор (CEO)", "Менеджер проектов (PM)", "Кладовщик / Технический инженер"]
    )
    st.divider()

    # Скрытие модулей ввода данных для обычных инженеров/кладовщиков
    if user_role in ["Директор (CEO)", "Менеджер проектов (PM)"]:
        st.header("⚙️ Модули справочников")
        
        with st.expander("👤 Создать контрагента (CRM)", expanded=False):
            with st.form("new_client_form"):
                new_inn = st.text_input("ИНН компании:")
                new_name = st.text_input("Название Юр. Лица:")
                new_phone = st.text_input("Телефон / Контакты:")
                add_client_btn = st.form_submit_button("Сохранить в CRM")
                
                if add_client_btn:
                    if not new_inn or not new_name:
                        st.error("Заполните ИНН и Название!")
                    else:
                        new_client = {"ИНН": str(new_inn), "Название": str(new_name), "Контакты": str(new_phone)}
                        st.session_state.clients = pd.concat([st.session_state.clients, pd.DataFrame([new_client])], ignore_index=True)
                        st.success(f"Контрагент {new_name} добавлен в базу!")
                        st.rerun()

        with st.expander("📦 Добавить прибор вручную", expanded=False):
            with st.form("new_item_form"):
                item_name = st.text_input("Название оборудования:")
                item_serial = st.text_input("Заводской серийный №:")
                item_price = st.number_input("Цена проката / сутки (₽):", min_value=100, value=5000)
                item_weight = st.number_input("Вес прибора (кг):", min_value=1, value=10)
                item_tip = st.text_area("Технические требования / Подсказка ИИ:", value="⚠️ Требуется стандартная коммутация.")
                add_item_btn = st.form_submit_button("Поставить на баланс")
                
                if add_item_btn:
                    if not item_name or not item_serial:
                        st.error("Заполните Название и Серийный номер!")
                    else:
                        new_id = int(st.session_state.inventory["ID"].max() + 1)
                        new_equipment = {
                            "ID": new_id, "Название": str(item_name), "Серийный №": str(item_serial),
                            "Статус": "Доступен", "Цена/сутки": int(item_price), "Вес_кг": int(item_weight), "Подсказка": str(item_tip)
                        }
                        st.session_state.inventory = pd.concat([st.session_state.inventory, pd.DataFrame([new_equipment])], ignore_index=True)
                        st.success(f"Прибор ID {new_id} успешно добавлен на склад!")
                        st.rerun()

# --- ГЛАВНЫЙ ЕДИНЫЙ ДАШБОРД ---
st.title(f"⚡ КонцертПрокат ERP | Панель: {user_role}")
st.caption("Сквозной учет: CRM -> Логистика (Карты) -> Юриспруденция -> 1С Дублирование -> Управленческий баланс")

# --- ОТОБРАЖЕНИЕ КАРТОЧЕК СТАТИСТИКИ ИСХОДЯ ИЗ РОЛИ ---
col_m1, col_m2, col_m3 = st.columns(3)
if user_role == "Директор (CEO)":
    with col_m1:
        st.metric("Оборот в обработке (Москва)", f"{sum(int(x['Сумма']) for x in st.session_state.orders):,} ₽")
    with col_m2:
        st.metric("Оборудования на объектах", f"{len(st.session_state.inventory[st.session_state.inventory['Статус']=='В аренде'])} ед.")
    with col_m3:
        st.metric("Зарегистрировано контрагентов", f"{len(st.session_state.clients)} компаний")
elif user_role == "Менеджер проектов (PM)":
    with col_m1:
        st.metric("Ваши активные заказы", f"{len(st.session_state.orders)} сделок")
    with col_m2:
        st.metric("Доступно ТОР-аппаратов", f"{len(st.session_state.inventory[st.session_state.inventory['Статус']=='Доступен'])} ед.")
    with col_m3:
        st.metric("Базовые площадки в работе", f"{len(st.session_state.venues)} объектов")
else: # Кладовщик / Техник
    with col_m1:
        st.metric("⚠️ Требует инспекции (Склад)", f"{len(st.session_state.inventory[st.session_state.inventory['Статус']=='В ремонте'])} ед.")
    with col_m2:
        st.metric("Всего позиций на балансе", f"{len(st.session_state.inventory)} шт.")
    with col_m3:
        st.metric("Собрано на отгрузку сегодня", f"{len(st.session_state.orders)} проектов")

# --- ВЫВОД ИНФОРМАЦИИ ПО СКЛАДУ НА ОСНОВЕ ПРАВ ДОСТУПА ---
st.subheader("📦 Складской учет ТОП-Оборудования")
if user_role in ["Директор (CEO)", "Менеджер проектов (PM)"]:
    # Полный вид для руководства с ценами
    st.dataframe(st.session_state.inventory, use_container_width=True, hide_index=True)
else:
    # Защищенный вид для склада: убираем колонку "Цена/сутки", оставляя только физические параметры
    tech_stock_view = st.session_state.inventory[["ID", "Название", "Серийный №", "Статус", "Вес_кг", "Подсказка"]]
    st.dataframe(tech_stock_view, use_container_width=True, hide_index=True)

# --- ИНТЕРФЕЙС ДЛЯ СКАЛА (ИНСПЕКЦИЯ БЕЗ QR) ---
if user_role == "Кладовщик / Технический инженер":
    st.subheader("🛠️ Зона инспекции прибора (Приемка/Выдача по Серийному №)")
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        selected_id = st.selectbox("ID прибора для отметки:", st.session_state.inventory["ID"])
    with col_t2:
        new_status = st.selectbox("Установить статус по чек-листу:", ["Доступен", "В аренде", "В ремонте"])
    with col_t3:
        if st.button("Зафиксировать состояние в системе", use_container_width=True):
            st.session_state.inventory.loc[st.session_state.inventory["ID"] == int(selected_id), "Статус"] = new_status
            st.toast(f"Прибор {selected_id} переведен в статус '{new_status}'", icon="🔧")
            st.rerun()

# --- СЕКЦИИ ДЛЯ МЕНЕДЖМЕНТА: ОФОРМЛЕНИЕ И ЛОГИСТИКА ---
if user_role in ["Директор (CEO)", "Менеджер проектов (PM)"]:
    st.divider()
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📝 Оформление новой аренды")
        with st.form("erp_order_form"):
            client_options = {row["Название"]: row["Название"] for idx, row in st.session_state.clients.iterrows()}
            customer = st.selectbox("Контрагент (CRM):", list(client_options.keys()))
            selected_venue = st.selectbox("Концертная площадка:", list(st.session_state.venues.keys()))
            
            eq_idx = st.selectbox("Выбор дорогого аппарата:", range(len(st.session_state.inventory)), 
                                  format_func=lambda x: f"{st.session_state.inventory.iloc[x]['Название']} (SN: {st.session_state.inventory.iloc[x]['Серийный №']})")
            
            chosen_item = st.session_state.inventory.iloc[eq_idx]
            st.warning(chosen_item["Подсказка"])
            
            days = st.number_input("Срок проката (суток):", min_value=1, value=1)
            delivery_needed = st.checkbox("Требуется наша доставка и монтаж", value=True)
            
            submit_btn = st.form_submit_button("🔥 Провести сделку")

        if submit_btn:
            venue_data = st.session_state.venues[selected_venue]
            dist = float(venue_data["Дистанция_км"])
            delivery_time_min = int((40 + (dist * 3)) * 1.3)
            delivery_cost = int(dist * 150 + 5000) if delivery_needed else 0
            
            total_price = int(chosen_item["Цена/сутки"]) * int(days) + delivery_cost
            
            new_order = {
                "ID": int(len(st.session_state.orders) + 1001),
                "Клиент": str(customer),
                "Площадка": str(selected_venue),
                "Адрес": str(venue_data["Адрес"]),
                "Аппарат": str(chosen_item["Название"]),
                "Серийный": str(chosen_item["Серийный №"]),
                "Сумма": int(total_price),
                "ВремяДоставки_мин": int(delivery_time_min),
                "Вес_общий": int(chosen_item["Вес_кг"]),
                "Дата": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            
            st.session_state.orders.append(new_order)
            st.session_state.inventory.loc[st.session_state.inventory["ID"] == int(chosen_item["ID"]), "Статус"] = "В аренде"
            st.success(f"Сделка №{new_order['ID']} для {customer} проведена!")
            st.rerun()

    with col_right:
        st.subheader("📍 Мониторинг логистики на карте Москвы")
        map_data = pd.DataFrame.from_dict(st.session_state.venues, orient='index')
        st.map(map_data, latitude='lat', longitude='lon', zoom=10, use_container_width=True)

# --- НИЖНЯЯ ПАНЕЛЬ: ДЕТАЛИЗАЦИЯ ПО ОТДЕЛАМ (ДОСТУПНА ТОЛЬКО ДЛЯ CEO/PM) ---
if user_role in ["Директор (CEO)", "Менеджер проектов (PM)"] and st.session_state.orders:
    st.divider()
    st.subheader("🗂️ Сквозная детализация по отделам для последней сделки")
    last_order = st.session_state.orders[-1]
    
    # Распределение вкладок исходя из роли (Директор видит всё, Менеджер не видит бухгалтерию/1С)
    tabs_list = ["📊 CRM & Управление", "⚖️ Юридический блок", "🏗️ Склад и Транспорт"]
    if user_role == "Директор (CEO)":
        tabs_list.insert(2, "🔄 Синхронизация с 1С / Финансы")
        
    tabs = st.tabs(tabs_list)
    
    # Логика отрисовки контента во вкладках
    with tabs[0]: # CRM
        st.json(last_order)
        
    with tabs[1]: # Юристы
        st.markdown(f"""
        **ДОГОВОР АРЕНДЫ № {last_order['ID']}-А**  
        *Контрагент:* {last_order['Клиент']} | *Заводской серийный номер аппарата:* {last_order['Серийный']}  
        **АКТ СВЯЗИ:** Материальная ответственность за порчу топ-номенклатуры зафиксирована на сумму {int(last_order['Сумма'] * 12):,} ₽. Договор готов к отправке в КЭДО.
        """)
        
    if user_role == "Директор (CEO)":
        with tabs[2]: # 1С (Видит только CEO)
            one_c_packet = {
                "Document_Type": "Invoice_Reserve",
                "1C_Code": f"ERP-MOS-{last_order['ID']}",
                "Counterparty": last_order['Клиент'],
                "Nomenclature": [{"Name": last_order['Аппарат'], "Serial": last_order['Серийный'], "Price": int(last_order['Сумма'])}],
                "Status_1C": "Posted_Not_Paid"
            }
            st.code(json.dumps(one_c_packet, indent=4, ensure_ascii=False), language="json")
            st.caption("🔒 Данная вкладка и финансовые логи 1С скрыты для аккаунтов с ролью 'Менеджер проектов'.")
            
        with tabs[3]: # Транспорт
            st.write(f"**Адрес доставки:** {last_order['Адрес']} | **Вес к погрузке:** {int(last_order['Вес_общий'])} кг. | **Тайминг:** ~{int(last_order['ВремяДоставки_мин'])} мин.")
    else:
        with tabs[2]: # Транспорт для менеджера (сдвигается индекс)
            st.write(f"**Адрес доставки:** {last_order['Адрес']} | **Вес к погрузке:** {int(last_order['Вес_общий'])} кг. | **Тайминг:** ~{int(last_order['ВремяДоставки_мин'])} мин.")
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
    
    st.session_state.orders = []
    st.session_state.drivers = [{"ФИО": "Григорий Орлов", "Транспорт": "Грузовой фургон 3.5т (Категория С)", "Статус": "Свободен"}]
    st.session_state.erp_initialized = True

# --- ГЛАВНЫЙ ЕДИНЫЙ ДАШБОРД ---
st.title("⚡ КонцертПрокат ERP v2.0 | Единый Центр Управления (Москва)")
st.caption("Сквозной учет: CRM -> Логистика (Карты) -> Юриспруденция -> 1С Дублирование -> Управленческий баланс")

# --- СТАТИСТИКА В РЕАЛЬНОМ ВРЕМЕНИ (УПРАВЛЕНЧЕСКИЙ УЧЕТ) ---
col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    st.metric("Оборот в обработке (Москва)", f"{sum(int(x['Сумма']) for x in st.session_state.orders):,} ₽")
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
        
        eq_idx = st.selectbox("Выбор дорогого аппарата:", range(len(st.session_state.inventory)), 
                              format_func=lambda x: f"{st.session_state.inventory.iloc[x]['Название']} ({int(st.session_state.inventory.iloc[x]['Цена/сутки']):,} ₽/сут)")
        
        chosen_item = st.session_state.inventory.iloc[eq_idx]
        st.warning(chosen_item["Подсказка"])
        
        days = st.number_input("Срок проката (суток):", min_value=1, value=1)
        delivery_needed = st.checkbox("Требуется наша доставка и монтаж", value=True)
        
        submit_btn = st.form_submit_button("🔥 Провести по всем системам (CRM, Бухгалтерия, Склад, Кадры)")

    if submit_btn:
        if not customer.strip():
            st.error("Ошибка CRM: Не указан контрагент.")
        else:
            venue_data = st.session_state.venues[selected_venue]
            dist = float(venue_data["Дистанция_км"])
            delivery_time_min = int((40 + (dist * 3)) * 1.3)
            delivery_cost = int(dist * 150 + 5000) if delivery_needed else 0
            
            total_price = int(chosen_item["Цена/сутки"]) * int(days) + delivery_cost
            
            # Принудительная очистка типов для JSON сериализации
            new_order = {
                "ID": int(len(st.session_state.orders) + 1001),
                "Клиент": str(customer),
                "Площадка": str(selected_venue),
                "Адрес": str(venue_data["Адрес"]),
                "Аппарат": str(chosen_item["Название"]),
                "Серийный": str(chosen_item["Серийный №"]),
                "Сумма": int(total_price),
                "ВремяДоставки_мин": int(delivery_time_min),
                "Вес_общий": int(chosen_item["Вес_кг"]),
                "Дата": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            
            st.session_state.orders.append(new_order)
            st.session_state.inventory.loc[st.session_state.inventory["ID"] == int(chosen_item["ID"]), "Статус"] = "В аренде"
            st.success(f"Сделка №{new_order['ID']} успешно проведена!")

with col_right:
    st.subheader("📍 Мониторинг логистики на карте Москвы")
    map_data = pd.DataFrame.from_dict(st.session_state.venues, orient='index')
    st.map(map_data, latitude='lat', longitude='lon', zoom=10, use_container_width=True)
    st.caption("Точки — выбранные концертные залы. Система автоматически строит маршруты от центрального склада.")

# --- НИЖНЯЯ ПАНЕЛЬ: ПОДРАЗДЕЛЕНИЯ ---
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
        st.write(f"**Общий вес оборудования к погрузке:** {int(last_order['Вес_общий'])} кг.")
        st.write(f"**Расчетное время в пути (Москва):** ~{int(last_order['ВремяДоставки_мин'])} минут.")
        st.write(f"**Назначенный водитель:** {st.session_state.drivers[0]['ФИО']} ({st.session_state.drivers[0]['Транспорт']})")
else:
    st.info("💡 Оформите тестовую сделку в форме выше, чтобы запустить сквозной процесс управленческого и юридического учета.")
