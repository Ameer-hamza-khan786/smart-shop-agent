import os
from datetime import date
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    Boolean,
    Date,
)

# --- DB Config ---
DATABASE_URL = "postgresql://postgres:hamza@localhost:5432/smartinventory"
engine = create_engine(DATABASE_URL)


with engine.connect() as conn:
    print("✅ Connected to PostgreSQL successfully!")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- MODELS ---


class Customer(Base):
    __tablename__ = "customers"
    cust_id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String)
    phone_no = Column(String)
    sales = relationship("SalesData", backref="customer")


class Vendor(Base):
    __tablename__ = "vendors"
    vend_id = Column(Integer, primary_key=True, index=True)
    vendor_name = Column(String)
    phone_no = Column(String)
    purchases = relationship("PurchaseData", backref="vendor")


class Product(Base):
    __tablename__ = "products"
    product_id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String, unique=True)
    price_purchase = Column(Float)
    price_sale = Column(Float)
    quantity = Column(Integer)


class SalesData(Base):
    __tablename__ = "sales_data"
    sales_id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.cust_id"))
    transaction_date = Column(Date)
    total_amount = Column(Float)
    total_quantity = Column(Integer)
    sale_products = relationship("SaleProduct", backref="sale")
    udhar = relationship("UdharSales", backref="sale", uselist=False)
    profit_loss = relationship("ProfitLoss", backref="sale", uselist=False)


class PurchaseData(Base):
    __tablename__ = "purchase_data"
    purch_id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.vend_id"))
    transaction_date = Column(Date)
    total_amount = Column(Float)
    total_quantity = Column(Integer)
    purchase_products = relationship("PurchaseProduct", backref="purchase")
    udhar = relationship("UdharPurchase", backref="purchase", uselist=False)


class ProfitLoss(Base):
    __tablename__ = "profit_loss"
    sales_id = Column(Integer, ForeignKey("sales_data.sales_id"), primary_key=True)
    is_profit = Column(Boolean)
    amount = Column(Float)


class SaleProduct(Base):
    __tablename__ = "sale_product"
    sales_id = Column(Integer, ForeignKey("sales_data.sales_id"), primary_key=True)
    prod_id = Column(Integer, ForeignKey("products.product_id"), primary_key=True)


class PurchaseProduct(Base):
    __tablename__ = "purchase_product"
    purch_id = Column(Integer, ForeignKey("purchase_data.purch_id"), primary_key=True)
    prod_id = Column(Integer, ForeignKey("products.product_id"), primary_key=True)


class UdharSales(Base):
    __tablename__ = "udhar_sales"
    udhar_id = Column(Integer, primary_key=True)
    sales_id = Column(Integer, ForeignKey("sales_data.sales_id"))
    date_of_entry = Column(Date)
    date_of_payment = Column(Date)


class UdharPurchase(Base):
    __tablename__ = "udhar_purchase"
    udhar_id = Column(Integer, primary_key=True)
    purch_id = Column(Integer, ForeignKey("purchase_data.purch_id"))
    date_of_entry = Column(Date)
    date_of_payment = Column(Date)


# --- DB Initialization ---


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Customers
        c1 = Customer(customer_name="Alice", phone_no="9991110001")
        c2 = Customer(customer_name="Bob", phone_no="9991110002")

        # Vendors
        v1 = Vendor(vendor_name="FreshFarms", phone_no="8881110001")
        v2 = Vendor(vendor_name="WholeGrain Ltd.", phone_no="8881110002")

        # Products
        p1 = Product(
            product_name="Rice", price_purchase=30.0, price_sale=40.0, quantity=100
        )
        p2 = Product(
            product_name="Oil", price_purchase=80.0, price_sale=100.0, quantity=50
        )

        # Sales
        s1 = SalesData(
            customer=c1,
            transaction_date=date(2024, 7, 1),
            total_amount=200.0,
            total_quantity=5,
        )

        s2 = SalesData(
            customer=c2,
            transaction_date=date(2024, 7, 2),
            total_amount=300.0,
            total_quantity=7,
        )

        # Purchases
        pur1 = PurchaseData(
            vendor=v1,
            transaction_date=date(2024, 6, 25),
            total_amount=500.0,
            total_quantity=15,
        )

        pur2 = PurchaseData(
            vendor=v2,
            transaction_date=date(2024, 6, 26),
            total_amount=600.0,
            total_quantity=20,
        )

        # Profit/loss
        pl1 = ProfitLoss(sales_id=1, is_profit=True, amount=100.0)
        pl2 = ProfitLoss(sales_id=2, is_profit=False, amount=-50.0)

        # Sale-product mappings
        sp1 = SaleProduct(sales_id=1, prod_id=1)
        sp2 = SaleProduct(sales_id=2, prod_id=2)

        # Purchase-product mappings
        pp1 = PurchaseProduct(purch_id=1, prod_id=1)
        pp2 = PurchaseProduct(purch_id=2, prod_id=2)

        # Udhar
        us1 = UdharSales(
            sales_id=1, date_of_entry=date(2024, 7, 1), date_of_payment=None
        )
        up1 = UdharPurchase(
            purch_id=1,
            date_of_entry=date(2024, 6, 25),
            date_of_payment=date(2024, 7, 5),
        )

        # Add all
        db.add_all(
            [
                c1,
                c2,
                v1,
                v2,
                p1,
                p2,
                s1,
                s2,
                pur1,
                pur2,
                pl1,
                pl2,
                sp1,
                sp2,
                pp1,
                pp2,
                us1,
                up1,
            ]
        )
        db.commit()
        print("✅ Database initialized with sample data.")

    except Exception as e:
        db.rollback()
        print("❌ Error initializing database:", e)

    finally:
        db.close()


Base.metadata.drop_all(bind=engine)


# --- DB Initialization for Original Model ---
def init_db_2():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Create 10 customers
        customers = [
            Customer(customer_name=f"Customer {i}", phone_no=f"999111{i:04}")
            for i in range(1, 11)
        ]

        # Create 5 vendors
        vendors = [
            Vendor(vendor_name=f"Vendor {i}", phone_no=f"888222{i:04}")
            for i in range(1, 6)
        ]

        # Create 20 products
        products = [
            Product(
                product_name=f"Product {i}",
                price_purchase=round(10 + (i % 20) + (i / 10), 2),  # $10-$30
                price_sale=round(15 + (i % 25) + (i / 8), 2),  # $15-$40
                quantity=50 + (i % 100),
            )
            for i in range(1, 21)
        ]

        # Create 30 sales transactions
        sales = []
        for i in range(1, 31):
            sales.append(
                SalesData(
                    customer=customers[i % len(customers)],
                    transaction_date=date(2024, (i % 12) + 1, (i % 28) + 1),
                    total_amount=round((i % 100) + 50 + (i / 10), 2),  # $50-$150
                    total_quantity=(i % 10) + 1,  # 1-10 items
                )
            )

        # Create 20 purchase transactions
        purchases = []
        for i in range(1, 21):
            purchases.append(
                PurchaseData(
                    vendor=vendors[i % len(vendors)],
                    transaction_date=date(2024, (i % 12) + 1, (i % 28) + 1),
                    total_amount=round((i % 500) + 100 + (i / 5), 2),  # $100-$600
                    total_quantity=(i % 20) + 5,  # 5-25 items
                )
            )

        # Add customers, vendors, products, sales, and purchases first
        initial_data = customers + vendors + products + sales + purchases
        db.add_all(initial_data)
        db.commit()  # Commit to get the auto-generated IDs

        # Now create profit/loss records using the committed sales IDs
        profit_loss = [
            ProfitLoss(
                sales_id=sale.sales_id,
                is_profit=i % 4 != 0,  # 75% profitable
                amount=round(sale.total_amount * 0.2 * (1 if i % 4 != 0 else -1), 2),
            )
            for i, sale in enumerate(sales)
        ]

        # Create the relationship records using the committed IDs
        sale_products = []
        for i, sale in enumerate(sales):
            # Add 1-3 products per sale
            for j in range(1, (i % 3) + 2):
                product = products[(i + j) % len(products)]
                sale_products.append(
                    SaleProduct(sales_id=sale.sales_id, prod_id=product.product_id)
                )

        purchase_products = []
        for i, purchase in enumerate(purchases):
            # Add 2-4 products per purchase
            for j in range(1, (i % 3) + 3):
                product = products[(i + j) % len(products)]
                purchase_products.append(
                    PurchaseProduct(
                        purch_id=purchase.purch_id, prod_id=product.product_id
                    )
                )

        # Create udhar (credit) records
        udhar_sales = [
            UdharSales(
                sales_id=sales[i].sales_id,
                date_of_entry=sales[i].transaction_date,
                date_of_payment=sales[i].transaction_date.replace(day=28)
                if i % 3 == 0
                else None,
            )
            for i in range(0, len(sales), 2)  # Every 2nd sale has udhar
        ]

        udhar_purchases = [
            UdharPurchase(
                purch_id=purchases[i].purch_id,
                date_of_entry=purchases[i].transaction_date,
                date_of_payment=purchases[i].transaction_date.replace(day=15)
                if i % 4 == 0
                else None,
            )
            for i in range(0, len(purchases), 3)  # Every 3rd purchase has udhar
        ]

        # Add the remaining data
        remaining_data = (
            sale_products
            + purchase_products
            + profit_loss
            + udhar_sales
            + udhar_purchases
        )
        db.add_all(remaining_data)
        db.commit()

        print(
            f"✅ Database initialized with:\n"
            f"- {len(customers)} customers\n"
            f"- {len(vendors)} vendors\n"
            f"- {len(products)} products\n"
            f"- {len(sales)} sales\n"
            f"- {len(purchases)} purchases\n"
            f"- {len(sale_products)} sale items\n"
            f"- {len(purchase_products)} purchase items\n"
            f"- {len(profit_loss)} profit/loss records\n"
            f"- {len(udhar_sales)} customer credit records\n"
            f"- {len(udhar_purchases)} vendor credit records"
        )

    except Exception as e:
        db.rollback()
        print("❌ Error initializing database:", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    try:
        # check if tables exist
        if not engine.dialect.has_table(engine.connect(), "customers"):
            init_db_2()
        else:
            print("✅ Database already initialized.")
    except Exception as e:
        print("❌ Error checking or creating the database:", e)
