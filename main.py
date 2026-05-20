import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta

# --- НАСТРОЙКА ИНТЕРФЕЙСА ПРИЛОЖЕНИЯ ---
st.set_page_config(page_title="Концерт-Прокат ERP Москва", page_icon="⚡", layout="wide")

# --- ИНИЦИАЛИЗАЦИЯ СКВОЗНОГО ЯДРА ДАННЫХ ---
if 'erp_initialized' not in st.session_state or 'clients' not in st.session_state:
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
    user_role = st.selectbox(
        "Выберите вашу должность:",
        ["Директор (CEO)", "Менеджер проектов (PM)", "Кладовщик / Технический инженер"]
    )
    st.divider()

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
else: # Кладовщик
    with col_m1:
        st.metric("⚠️ Требует инспекции (Склад)", f"{len(st.session_state.inventory[st.session_state.inventory['Статус']=='В ремонте'])} ед.")
    with col_m2:
        st.metric("Всего позиций на балансе", f"{len(st.session_state.inventory)} шт.")
    with col_m3:
        st.metric("Собрано на отгрузку сегодня", f"{len(st.session_state.orders)} проектов")

# --- ВЫВОД ИНФОРМАЦИИ ПО СКЛАДУ НА ОСНОВЕ ПРАВ ДОСТУПА ---
st.subheader("📦 Складской учет ТОП-Оборудования")
if user_role in ["Директор (CEO)", "Менеджер проектов (PM)"]:
    st.dataframe(st.session_state.inventory, use_container_width=True, hide_index=True)
else:
    tech_stock_view = st.session_state.inventory[["ID", "Название", "Серийный №", "Статус", "Вес_кг", "Подсказка"]]
    st.dataframe(tech_stock_view, use_container_width=True, hide_index=True)

# --- ИНТЕРФЕЙС ДЛЯ СКЛАДА (ИНСПЕКЦИЯ БЕЗ QR) ---
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

# --- НИЖНЯЯ ПАНЕЛЬ: ДЕТАЛИЗАЦИЯ ПО ОТДЕЛАМ ---
if user_role in ["Директор (CEO)", "Менеджер проектов (PM)"] and st.session_state.orders:
    st.divider()
    st.subheader("🗂️ Сквозная детализация по отделам для последней сделки")
    last_order = st.session_state.orders[-1]
    
    # Исправленное и безопасное распределение вкладок через явные переменные
    if user_role == "Директор (CEO)":
        t_crm, t_legal, t_1c, t_wh = st.tabs(["📊 CRM & Управление", "⚖️ Юридический блок", "🔄 Синхронизация с 1С / Финансы", "🏗️ Склад и Транспорт"])
    else:
        t_crm, t_legal, t_wh = st.tabs(["📊 CRM & Управление", "⚖️ Юридический блок", "🏗️ Склад и Транспорт"])
        t_1c = None
        
    with t_crm:
        st.json(last_order)
        
    with t_legal:
        st.markdown(f"""
        **ДОГОВОР АРЕНДЫ № {last_order['ID']}-А**  
        *Контрагент:* {last_order['Клиент']} | *Заводской серийный номер аппарата:* {last_order['Серийный']}  
        **АКТ СВЯЗИ:** Материальная ответственность за порчу топ-номенклатуры зафиксирована на сумму {int(last_order['Сумма'] * 12):,} ₽. Договор готов к отправке в КЭДО.
        """)
        
    if t_1c is not None:
        with t_1c:
            one_c_packet = {
                "Document_Type": "Invoice_Reserve",
                "1C_Code": f"ERP-MOS-{last_order['ID']}",
                "Counterparty": last_order['Клиент'],
                "Nomenclature": [{"Name": last_order['Аппарат'], "Serial": last_order['Серийный'], "Price": int(last_order['Сумма'])}],
                "Status_1C": "Posted_Not_Paid"
            }
            st.code(json.dumps(one_c_packet, indent=4, ensure_ascii=False), language="json")
            st.caption("🔒 Данная вкладка и финансовые логи 1С скрыты для аккаунтов с ролью 'Менеджер проектов'.")
            
    with t_wh:
        st.write(f"**Адрес доставки:** {last_order['Адрес']} | **Вес к погрузке:** {int(last_order['Вес_общий'])} кг. | **Тайминг:** ~{int(last_order['ВремяДоставки_мин'])} мин.")
