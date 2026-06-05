from database import Session, engine
from database_models import Base, Product


SAMPLE_PRODUCTS = [
    {
        "name": "Starter Plan",
        "description": "Self-serve subscription plan for early-stage teams",
        "price": 49,
        "quantity": 42,
    },
    {
        "name": "Growth Plan",
        "description": "Collaboration plan for scaling SaaS product teams",
        "price": 149,
        "quantity": 18,
    },
    {
        "name": "Enterprise Plan",
        "description": "Advanced governance and support for large accounts",
        "price": 499,
        "quantity": 6,
    },
    {
        "name": "Analytics Add-on",
        "description": "Product analytics module for funnel and feature reporting",
        "price": 89,
        "quantity": 5,
    },
    {
        "name": "Priority Support",
        "description": "Premium support package with faster response times",
        "price": 199,
        "quantity": 0,
    },
]


def seed_products():
    Base.metadata.create_all(bind=engine)
    db = Session()

    try:
        for item in SAMPLE_PRODUCTS:
            exists = db.query(Product).filter(Product.name == item["name"]).first()
            if not exists:
                db.add(Product(**item))

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed_products()
    print(f"Seeded {len(SAMPLE_PRODUCTS)} SaaS products.")
