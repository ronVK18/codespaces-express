from fastapi import FastAPI
import joblib
import xgboost as xgb
import numpy as np
from pydantic import BaseModel
app = FastAPI()
model = joblib.load("m.pkl")
class Transaction(BaseModel):
    step: int
    type: int  # Assuming this is categorical encoded (0-4 for example)
    amount: float
    oldbalanceOrg: float
    newbalanceOrig: float
    oldbalanceDest: float
    newbalanceDest: float
    balance_change_org: float
    balance_change_dest: float

@app.get("/")
def read_root():
    return {"message": "Welcome to the FastAPI website!"}
@app.post("/predict")
def predict(transaction: Transaction):
    print("Received input data:", transaction) 
    data = np.array([[transaction.step, transaction.type, transaction.amount,
                      transaction.oldbalanceOrg, transaction.newbalanceOrig,
                      transaction.oldbalanceDest, transaction.newbalanceDest,
                      transaction.balance_change_org, transaction.balance_change_dest]])
    # dmatrix = xgb.DMatrix(data)
    prediction = model.predict(data)
    return {"prediction": int(prediction[0])}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)