import streamlit as st
import pandas as pd

st.set_page_config(page_title="Latest Prices Dashboard", layout="wide")

st.title("Latest Purchase Prices – Wonderzyme")

# File uploader
uploaded_file = st.file_uploader("Upload your Purchase Order Excel file", type=["xlsx", "xls"])

if uploaded_file is not None:
    with st.spinner("Reading Excel file..."):
        try:
            # Auto-detect skiprows
            df = None
            for skip in [0, 3, 4, 5, 6]:
                temp = pd.read_excel(uploaded_file, dtype=str, skiprows=skip)
                cols_lower = [str(c).lower().strip() for c in temp.columns]
                if any(word in ' '.join(cols_lower) for word in ['description', 'price', 'date', 'qty', 'unit', 'po#']):
                    df = temp
                    st.caption(f"Headers detected after skipping {skip} rows")
                    break

            if df is None:
                df = pd.read_excel(uploaded_file, dtype=str, skiprows=4)
                st.warning("Fallback: skipped 4 rows. If columns are wrong, edit skiprows (try 3,5,6).")

            # Show columns
            st.caption("Columns found in file:")
            st.write(list(df.columns))

            # Column mapping
            possible_product_cols = ['DESCRIPTION', 'description', 'Product', 'DESC']
            possible_price_cols   = ['UNIT PRICE', 'Unit Price', 'PRICE', 'U/P']
            possible_date_cols    = ['DATE', 'Date', 'PO DATE', 'Order Date', 'DELIVERY DATE']
            possible_supplier_cols= ['NAME', 'Supplier', 'Vendor']
            possible_qty_cols     = ['QTY', 'Quantity', 'Qty']
            possible_unit_cols    = ['UNIT', 'Unit']

            def find_col(possibles, df_cols):
                for p in possibles:
                    for col in df_cols:
                        if p.lower() in str(col).lower():
                            return col
                return None

            col_product   = find_col(possible_product_cols, df.columns) or df.columns[6]
            col_price     = find_col(possible_price_cols, df.columns) or df.columns[7]
            col_date      = find_col(possible_date_cols, df.columns) or df.columns[2]
            col_supplier  = find_col(possible_supplier_cols, df.columns) or df.columns[3]
            col_qty       = find_col(possible_qty_cols, df.columns) or df.columns[4]
            col_unit      = find_col(possible_unit_cols, df.columns) or df.columns[5]

            st.caption(f"Detected → Product: {col_product} | Price: {col_price} | Date: {col_date} | Supplier: {col_supplier}")

            # Convert numeric columns
            df[col_price] = pd.to_numeric(df[col_price], errors='coerce')
            df[col_qty]   = pd.to_numeric(df[col_qty], errors='coerce')

            # Date conversion - flexible for string dates
            df['parsed_date'] = pd.to_datetime(df[col_date], errors='coerce', format='mixed')

            # Clean rows
            df = df.dropna(how='all')
            df = df[df[col_product].notna() & df[col_product].astype(str).str.strip().ne('')]

            if df.empty:
                st.error("No valid data rows found. Try different skiprows.")
                st.stop()

            # Latest per product + supplier
            latest_df = (
                df.sort_values('parsed_date', ascending=False)
                  .groupby([col_product, col_supplier], as_index=False)
                  .first()
            )

            display_cols = [col_product, col_supplier, col_price, 'parsed_date', col_qty, col_unit]
            display_df = latest_df[display_cols].copy()

            display_df = display_df.rename(columns={
                col_product: 'Product',
                col_supplier: 'Supplier',
                col_price: 'Latest Unit Price',
                'parsed_date': 'Latest Date',
                col_qty: 'Qty',
                col_unit: 'Unit'
            })

            display_df['Latest Unit Price'] = display_df['Latest Unit Price'].round(2)
            display_df['Latest Date'] = display_df['Latest Date'].dt.strftime('%Y-%m-%d').where(
                display_df['Latest Date'].notna(), 'Invalid Date')

            # ─── Dashboard ────────────────────────────────────────────────

            st.success(f"Loaded {len(display_df)} unique product-supplier combinations")

            # Supplier dropdown (big single-select for "all products from one supplier")
            all_suppliers = ["All Suppliers"] + sorted(df[col_supplier].dropna().unique().tolist())
            selected_supplier = st.selectbox(
                "Show all products from this supplier",
                options=all_suppliers,
                index=0,  # default to All Suppliers
                help="Select a supplier to see only their products and latest prices"
            )

            # Product search
            search_term = st.text_input("Search product name", "")

            # Start with full latest data
            filtered = display_df.copy()

            # Apply supplier filter
            if selected_supplier != "All Suppliers":
                filtered = filtered[filtered['Supplier'] == selected_supplier]

            # Apply product search
            if search_term:
                filtered = filtered[
                    filtered['Product'].astype(str).str.contains(search_term, case=False, na=False)
                ]

            # Show filtered table
            st.dataframe(
                filtered.sort_values("Latest Date", ascending=False),
                use_container_width=True,
                column_config={
                    "Latest Unit Price": st.column_config.NumberColumn("Latest Unit Price", format="₱ %,.2f"),
                    "Latest Date": st.column_config.TextColumn("Latest Date"),
                },
                hide_index=True
            )

            # Show result count if filtered
            if len(filtered) < len(display_df):
                st.caption(f"Showing {len(filtered)} matching combinations")

            # History view (still per product, shows all suppliers)
            st.subheader("View full history of a product")
            selected_product = st.selectbox(
                "Select product",
                options=sorted(df[col_product].dropna().unique()),
                index=None,
                placeholder="Choose one..."
            )

            if selected_product:
                history = df[df[col_product] == selected_product].copy()
                history = history.sort_values('parsed_date', ascending=False)
                history['parsed_date'] = history['parsed_date'].dt.strftime('%Y-%m-%d').where(
                    history['parsed_date'].notna(), 'Invalid Date')
                st.dataframe(
                    history[[col_date, col_supplier, col_qty, col_unit, col_price]],
                    column_config={col_price: st.column_config.NumberColumn(format="₱ %,.2f")},
                    hide_index=True,
                    use_container_width=True
                )

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.info("Try changing skiprows value in code or ensure file isn't open elsewhere.")

else:
    st.info("Upload your Purchase Order Excel file to start.")
    st.markdown("""
    **Quick fixes if needed**:
    - If columns are still "Unnamed:", change skiprows=4 → try 3, 5 or 6
    - If dates show as Invalid, tell me how dates look in Excel
    """)