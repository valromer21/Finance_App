import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

# Set the page configuration and give it title

st.set_page_config(page_title="Chinyi Finance App", page_icon="🐹", layout="wide")

category_file = "categories.json"

if "categories" not in st.session_state:
    #Se configuran las categorias por defecto
    st.session_state.categories = {
        "General":[]
    }

if os.path.exists(category_file):
    # Si se han creado categorias previamente, se cargan desde el archivo JSON
    with open(category_file, "r") as f:
        st.session_state.categories = json.load(f)

def save_categories():
    # Se guardan las categorias en un archivo JSON
    with open(category_file, "w") as f:
        json.dump(st.session_state.categories, f)

def categorize_transaction(df):
    df["Category"] = "General"  # Asignar categoría por defecto

    # Aplicar la categorización de las transacciones en base a palabras clave
    for category, keywords in st.session_state.categories.items():
        if category == "General" or not keywords:
            continue
        # Se normalizan para que sean mas faciles de comparar
        lowered_keywords = [keyword.lower().strip() for keyword in keywords]

        # Ciclo para recorrer las palabras clave y asignar la categoría
        for idx, row in df.iterrows():
            #Se obtienen los detalles de las transacciones
            details = row["Details"].lower().strip()
            #Se revisa si alguna de las palabras clave esta en los detalles de la transacción
            if details in lowered_keywords:
                # Si se encuentra una palabra clave, se asigna la categoría
                df.at[idx, "Category"] = category
    return df

def load_transactions(file):
    try:
        df = pd.read_csv(file)
        # Eliminando espacios en blanco de los nombres de las columnas
        df.columns = [col.strip() for col in df.columns]
        # Normalizando los valores de la columna "Amount" para que sean validos
        df["Amount"] = df["Amount"].str.replace(",", "").astype(float)
        # Se normalizan las fechas para que sean validas
        df["Date"]= pd.to_datetime(df["Date"], format="%d %b %Y")

        return categorize_transaction(df)
    except Exception as e:
        st.error(f"Hubo un error al procesar el archivo: {str(e)}")
        return

def add_keywprd_to_category(category, keyword):
    # Funcion para añadir una palabra clave a una categoría existente
    keyword = keyword.strip()

    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        save_categories()
        st.success(f"Palabra clave '{keyword}' añadida a la categoría '{category}'.", icon="✅")
        return True
    return False
        

def main():
    st.title("Finance Dashboard")
    #Funcion para que la persona suba sus datos
    uploaded_file = st.file_uploader("Sube tu archivo bancario CSV", type=["csv"])

    if uploaded_file is not None:
        df = load_transactions(uploaded_file)

        if df is not None:
            # Se separan los valores de la columna "Debit/Credit" en dos dataframes
            debits_df = df[df["Debit/Credit"] == "Debit"].copy()
            credits_df = df[df["Debit/Credit"] == "Credit"].copy()

            st.session_state.debits_df = debits_df.copy()

            #Se configura unas pestañas para visualizar los datos credito/debito
            tab1, tab2 = st.tabs(["Gastos (Débitos)", "Pagos - Cuotas (Créditos)"])
            with tab1:
                # Se permite al usuario crear sus categorías
                new_category = st.text_input("Añadir nueva categoría:")
                # Boton para añadir la nueva categoría
                add_button = st.button("Añadir categoría")

                if add_button and new_category:
                    if new_category not in st.session_state.categories:
                        st.session_state.categories[new_category] = []
                        save_categories()
                        st.success(f"Categoría '{new_category}' añadida.", icon="✅")
                        st.rerun()

                st.subheader("Tus gastos")
                edited_df = st.data_editor(
                    st.session_state.debits_df[["Date", "Details", "Amount", "Category"]], # se seleccionan las columnas a mostrar
                    column_config={
                        "Date": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                        "Amount": st.column_config.NumberColumn("Monto", format="%.2f EAD"),
                        "Category": st.column_config.SelectboxColumn(
                            "Categoria", 
                            options=list(st.session_state.categories.keys()), 
                        )
                    },
                    hide_index = True,
                    use_container_width = True,
                    key = "Category_editor"
                )

                save_button = st.button("Guardar cambios", type="primary")
                if save_button:
                    for idx, row in edited_df.iterrows():
                        new_category = row["Category"]
                        # Se compara con el dataframe original para ver si hay cambios
                        if new_category == st.session_state.debits_df.at[idx, "Category"]:
                            continue
                        # Si hay cambios, se actualiza el dataframe original
                        details = row["Details"]
                        st.session_state.debits_df.at[idx, "Category"] = new_category
                        add_keywprd_to_category(new_category, details)

                st.subheader("Resumen de gastos")
                # Se revisa el data, se suma y se reinicia el indice
                category_totals= st.session_state.debits_df.groupby("Category")["Amount"].sum().reset_index()
                # Se mejora la visualización de los datos
                category_totals = category_totals.sort_values(by="Amount", ascending=False)

                st.dataframe(
                    category_totals,
                    column_config={
                        "Amount": st.column_config.NumberColumn("Total Gastos", format="%.2f EAD")
                    },
                    use_container_width=True,
                    hide_index=True
                )

                fig = px.pie(
                    category_totals, 
                    values="Amount", 
                    names="Category", 
                    title="Distribución de Gastos por Categoría",
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                st.subheader("Total de Tus pagos - cuotas")
                total_payments = credits_df["Amount"].sum()
                st.metric("Total Pagos - Cuotas", f"{total_payments:,.2f} EAD")
                st.write(credits_df)
main ()