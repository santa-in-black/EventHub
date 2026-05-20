import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta

# --- НАСТРОЙКА ИНТЕРФЕЙСА ПРИЛОЖЕНИЯ (ОБЯЗАТЕЛЬНО ПЕРВАЯ КОМАНДА) ---
st.set_page_config(page_title="Концерт-Прокат ERP Москва", page_icon="⚡", layout="wide")

# --- ИНИЦИАЛИЗАЦИЯ СКВОЗНОГО ЯДРА ДАННЫХ (БАЗА SPINOFF) ---
if 'erp_initialized' not in st.session_state or 'clients' not in st.session_state:
    # 1. Реальная номенклатура со средними ценами по Москве (на основе spinoff.ru)
    st.session_state.inventory = pd.DataFrame([
        {"ID": 501, "Название": "Звуковой комплект L-Acoustics K2 (Line Array)", "Серийный №": "SPIN-LA-K2-01", "Статус": "Доступен", "Цена/сутки": 120000, "Вес_кг": 670, "Подсказка": "⚠️ Требуется: 3-фазное питание 32А, лод-мастер, лебедки 1т."},
        {"ID": 502, "Название": "Световой пульт grandMA2 Full Size", "Серийный №": "SPIN-GMA2-FS9", "Статус": "Доступен", "Цена/сутки": 25000, "Вес_кг": 50, "Подсказка": "⚠️ Требуется: ИБП 2кВт, резервный пульт grandMA2 light."},
        {"ID": 503, "Название": "Прибор эффектов Light Sky IP3000 Aqua Beam", "Серийный №": "SPIN-LS-AQ30", "Статус": "В аренде", "Цена/сутки": 4000, "Вес_кг": 38, "Подсказка": "⚠️ Всепогодный IP65. Идеален для стадионных опен-эйров."},
        {"ID": 504, "Название": "Сценический станок 2х1м (модуль сцены)", "Серийный №": "SPIN-STAGE-01", "Статус": "Доступен", "Цена/сутки": 1250, "Вес_кг": 32, "Подсказка": "⚠️ Комплектуется ножками (40/60/80/100 см) и струбцинами."}
    ])
    
    # 2. База контрагентов (Интегрирована реальная компания SPINOFF)
    st.session_state.clients = pd.DataFrame([
        {"ИНН": "7734445566", "Название": "ООО 'СПИНОФФ ТЕХНИКАЛ ПРОДАКШН'", "Ген. Директор": "Вася Санюк", "Контакты": "+7 (985) 769-52-22", "Сайт": "spinoff.ru"},
        {"ИНН": "7702998877", "Название": "АО 'Крокус Ивентс'", "Ген. Директор": "Агаларов Э.М.", "Контакты": "+7 (495) 777-88-99", "Сайт": "crocus-hall.ru"}
    ])
    
    # 3. Реестр концертных площадок Москвы (с координатами)
    st.session_state.venues = {
        "ВТБ Арена": {"lat": 55.7915, "lon": 37.5601, "Адрес": "Ленинградский просп., 36", "Дистанция_км": 9},
        "Crocus City Hall": {"lat": 55.8251, "lon": 37.3902, "Адрес": "МКАД 66-й км", "Дистанция_км": 22},
        "MTS Live Холл": {"lat": 55.7499, "lon": 37.6978, "Адрес": "шоссе Энтузиастов, 5", "Дистанция_км": 6},
        "Красная Площадь (Опен-эйр)": {"lat": 55.7539, "lon": 37.6208, "Адрес": "Красная площадь", "Дистанция_км": 1}
    }
    
    st.session_state.orders = []
    st.session_state.drivers = [{"ФИО": "Григорий Орлов", "Транспорт": "Грузовой фургон 3.5т", "Статус": "Свободен"}]
    st.session_state.erp_initialized = True

# --- БОКОВАЯ ПАНЕЛЬ: АВТОРИЗАЦИЯ И РАСШИРЕННЫЙ ВВОД ---
with st.sidebar:
    st.header("🔑 Должностной доступ")
    user_role = st.selectbox(
        "Выберите вашу должность:",
        ["Директор (CEO)", "Менеджер проектов (PM)", "Кладовщик / Технический инженер"]
    )
    st.divider()

    if user_role in ["Директор (CEO)", "Менеджер проектов (PM)"]:
        st.header("⚙️ Модули ввода данных")
        
        with st.expander("👤 Завести контрагента (CRM)", expanded=False):
            with st.form("new_client_form"):
                new_inn = st.text_input("ИНН компании:")
                new_name = st.text_input("Название Юр. Лица:")
                new_ceo = st.text_input("Ген. Директор (ФИО):")
                new_phone = st.text_input("Телефон:")
                add_client_btn = st.form_submit_button("Сохранить в CRM")
                
                if add_client_btn:
                    if not new_inn or not new_name:
                        st.error("Заполните ИНН и Название компании!")
                    else:
                        new_client = {
                            "ИНН": str(new_inn), "Название": str(new_name), 
                            "Ген. Директор": str(new_ceo), "Контакты": str(new_phone), "Сайт": "Вручную"
                        }
                        st.session_state.clients = pd.concat([st.session_state.clients, pd.DataFrame([new_client])], ignore_index=True)
                        st.success(f"Контрагент {new_name} добавлен в базу CRM!")
                        st.rerun()

        with st.expander("📦 Добавить прибор вручную", expanded=False):
            with st.form("new_item_form"):
                item_name = st.text_input("Название оборудования:")
                item_serial = st.text_input("Заводской серийный №:")
                item_price = st.number_input("Цена проката / сутки (₽):", min_value=100, value=5000)
                item_weight = st.number_input("Вес прибора (кг):", min_value=1, value=10)
                item_tip = st.text_area("Подсказка / Требования:", value="⚠️ Специфических требований нет.")
                add_item_btn = st.form_submit_button("Поставить на баланс")
                
                if add_item_btn:
                    if not item_name or not item_serial:
                        st.error("Укажите название и заводской серийный номер!")
                    else:
                        new_id = int(st.session_state.inventory["ID"].max() + 1)
                        new_equipment = {
                            "ID": new_id, "Название": str(item_name), "Серийный №": str(item_serial),
                            "Статус": "Доступен", "Цена/сутки": int(item_price), "Вес_кг": int(item_weight), "Подсказка": str(item_tip)
                        }
                        st.session_state.inventory = pd.concat([st.session_state.inventory, pd.DataFrame([new_equipment])], ignore_index=True)
                        st.success(f"Прибор ID {new_id} добавлен на баланс склада!")
                        st.rerun()

# --- ГЛАВНЫЙ ЕДИНЫЙ ДАШБОРД ---
st.title(f"⚡ КонцертПрокат ERP | База: SPINOFF PRODUCTION")
st.caption(f"Просмотр интерфейса под ролью: {user_role}. Синхронизация данных: Активна.")

col_m1, col_m2, col_m3 = st.columns(3)
if user_role == "Директор (CEO)":
    with col_m1:
        st.metric("Оборот в обработке (Москва)", f"{sum(int(x.get('Сумма', 0)) for x in st.session_state.orders):,} ₽")
    with col_m2:
        st.metric("Оборудования в аренде", f"{len(st.session_state.inventory[st.session_state.inventory['Статус']=='В аренде'])} ед.")
    with col_m3:
        st.metric("Контрагенты в CRM", f"{len(st.session_state.clients)} компаний")
else:
    with col_m1:
        st.metric("Заказы на сборку", f"{len(st.session_state.orders)} проектов")
    with col_m2:
        st.metric("Всего позиций на складе", f"{len(st.session_state.inventory)} ед.")
    with col_m3:
        st.metric("Точки доставки (Москва)", f"{len(st.session_state.venues)} залов")

st.subheader("📋 Реестр дорогостоящей техники (Серийный учет)")
if user_role in ["Директор (CEO)", "Менеджер проектов (PM)"]:
    st.dataframe(st.session_state.inventory, use_container_width=True, hide_index=True)
else:
    st.dataframe(st.session_state.inventory[["ID", "Название", "Серийный №", "Статус", "Вес_кг", "Подсказка"]], use_container_width=True, hide_index=True)

if user_role == "Кладовщик / Технический инженер":
    st.subheader("🛠️ Приемка / Выдача приборов без QR-маркировки")
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        selected_id = st.selectbox("Выберите ID прибора:", st.session_state.inventory["ID"])
    with col_t2:
        new_status = st.selectbox("Изменить статус после инспекции:", ["Доступен", "В аренде", "В ремонте"])
    with col_t3:
        if st.button("Зафиксировать статус прибора", use_container_width=True):
            st.session_state.inventory.loc[st.session_state.inventory["ID"] == int(selected_id), "Статус"] = new_status
            st.toast("Статус обновлен в базе!", icon="⚙️")
            st.rerun()

if user_role in ["Директор (CEO)", "Менеджер проектов (PM)"]:
    st.divider()
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📝 Оформить аренду концертного оборудования")
        with st.form("erp_order_form"):
            client_map = {row["Название"]: row for idx, row in st.session_state.clients.iterrows()}
            customer_name = st.selectbox("Выберите заказчика из базы CRM:", list(client_map.keys()))
            selected_venue = st.selectbox("Концертная площадка (Москва):", list(st.session_state.venues.keys()))
            
            eq_idx = st.selectbox("Выбор аппарата под проект:", range(len(st.session_state.inventory)), 
                                  format_func=lambda x: f"{st.session_state.inventory.iloc[x]['Название']} (Цена: {int(st.session_state.inventory.iloc[x]['Цена/сутки']):,} ₽)")
            
            chosen_item = st.session_state.inventory.iloc[eq_idx]
            st.warning(chosen_item["Подсказка"])
            
            days = st.number_input("Длительность проката (суток):", min_value=1, value=1)
            delivery_needed = st.checkbox("Требуется логистика и технический монтаж Spinoff", value=True)
            
            submit_btn = st.form_submit_button("🔥 Провести по всем балансам компании")

        if submit_btn:
            venue_data = st.session_state.venues[selected_venue]
            dist = float(venue_data["Дистанция_км"])
            delivery_time_min = int((40 + (dist * 3)) * 1.3)
            delivery_cost = int(dist * 150 + 5000) if delivery_needed else 0
            
            total_price = int(chosen_item["Цена/сутки"]) * int(days) + delivery_cost
            client_data = client_map[customer_name]
            
            new_order = {
                "ID": int(len(st.session_state.orders) + 1001),
                "Клиент": str(customer_name),
                "Ген_Директор": str(client_data.get("Ген. Директор", "Вася Санюк")),
                "ИНН": str(client_data.get("ИНН", "7734445566")),
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
            st.success(f"Сделка успешно проведена для {customer_name}!")
            st.rerun()

    with col_right:
        st.subheader("📍 Логистическая карта и мониторинг транспорта")
        map_data = pd.DataFrame.from_dict(st.session_state.venues, orient='index')
        st.map(map_data, latitude='lat', longitude='lon', zoom=10, use_container_width=True)

# --- НИЖНЯЯ ПАНЕЛЬ: ДЕТАЛИЗАЦИЯ ПО ОТДЕЛАМ ---
if user_role in ["Директор (CEO)", "Менеджер проектов (PM)"] and st.session_state.orders:
    st.divider()
    st.subheader("🗂️ Сквозная детализация по отделам для последней сделки")
    last_order = st.session_state.orders[-1]
    
    if user_role == "Директор (CEO)":
        t_crm, t_legal, t_1c, t_wh = st.tabs(["📊 CRM & Управление", "⚖️ Юридический блок", "🔄 Синхронизация с 1С / Финансы", "🏗️ Склад и ТТК"])
    else:
        t_crm, t_legal, t_wh = st.tabs(["📊 CRM & Управление", "⚖️ Юридический блок", "🏗️ Склад и ТТК"])
        t_1c = None
        
    with t_crm:
        st.json(last_order)
        
    with t_legal:
        st.markdown(f"""
        **ДОГОВОР АРЕНДЫ № {last_order.get('ID', 1001)}-А**  
        *Исполнитель:* ООО "СПИНОФФ ТЕХНИКАЛ ПРОДАКШН"  
        *Заказчик:* {last_order.get('Клиент', 'Не указан')} (ИНН: {last_order.get('ИНН', '7734445566')}) в лице Генерального директора **{last_order.get('Ген_Директор', 'Вася Санюк')}**.  
        
        **ПРЕДМЕТ ДОГОВОРА:**  
        Передача во временное пользование концертного оборудования: **{last_order.get('Аппарат', 'Комплект')}** (Заводской серийный номер: **{last_order.get('Серийный', 'SN')}**).  
        """)
        
    if t_1c is not None:
        with t_1c:
            one_c_packet = {
                "Document_Type": "Invoice_Reserve",
                "1C_Code": f"ERP-SPINOFF-{last_order.get('ID', 1001)}",
                "Counterparty": last_order.get('Клиент', 'Не указан'),
                "Nomenclature": [{"Name": last_order.get('Аппарат', 'Комплект'), "Serial": last_order.get('Серийный', 'SN'), "Price": int(last_order.get('Сумма', 0))}],
                "Status_1C": "Posted_Not_Paid"
            }
            st.code(json.dumps(one_c_packet, indent=4, ensure_ascii=False), language="json")
            
    with t_wh:
        st.write(f"**Пункт доставки:** {last_order.get('Площадка')} ({last_order.get('Адрес')})")
        st.write(f"**Масса груза:** {int(last_order.get('Вес_общий', 0))} кг. | **Тайминг доставки по Москве:** ~{int(last_order.get('ВремяДоставки_мин', 0))} мин.")
