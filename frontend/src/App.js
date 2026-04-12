

import React, { useEffect, useState } from "react";
import "./App.css";

const BASE_URL = "http://127.0.0.1:8000";

function App() {
  const [products, setProducts] = useState([]);

  // ❌ REMOVED id from form (backend auto-generates it)
  const [form, setForm] = useState({
    name: "",
    description: "",
    price: "",
    quantity: ""
  });

  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [toast, setToast] = useState("");

  useEffect(() => {
    fetchProducts();
  }, []);

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(""), 2000);
  };

  // ✅ Added error handling
  const fetchProducts = async () => {
    try {
      setLoading(true);

      const res = await fetch(`${BASE_URL}/products`);

      if (!res.ok) {
        throw new Error("Failed to fetch products");
      }

      const data = await res.json();
      setProducts(data);

    } catch (err) {
      console.error(err);
      showToast("Error fetching products ❌");
    } finally {
      setLoading(false);
    }
  };

  // ✅ FIXED: Do NOT send id
  const addProduct = async () => {
    try {
      const res = await fetch(`${BASE_URL}/products`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: form.name,
          description: form.description,
          price: Number(form.price),
          quantity: Number(form.quantity)
        })
      });

      // ✅ handle backend validation errors
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to add product");
      }

      showToast("Product Added ✅");

      // ✅ reset form after adding
      setForm({
        name: "",
        description: "",
        price: "",
        quantity: ""
      });

      fetchProducts();

    } catch (err) {
      console.error(err);
      showToast(err.message || "Error adding product ❌");
    }
  };

  // ✅ FIXED: send only required fields (no id in body)
  const updateProduct = async () => {
    try {
      const res = await fetch(`${BASE_URL}/products/${form.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: form.name,
          description: form.description,
          price: Number(form.price),
          quantity: Number(form.quantity)
        })
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to update product");
      }

      setShowModal(false);
      showToast("Product Updated ✏️");
      fetchProducts();

    } catch (err) {
      console.error(err);
      showToast(err.message || "Error updating ❌");
    }
  };

  // ✅ Added error handling
  const deleteProduct = async (id) => {
    try {
      const res = await fetch(`${BASE_URL}/products/${id}`, {
        method: "DELETE"
      });

      if (!res.ok) {
        throw new Error("Failed to delete product");
      }

      showToast("Product Deleted ❌");
      fetchProducts();

    } catch (err) {
      console.error(err);
      showToast("Error deleting ❌");
    }
  };

  // ✅ Keep id only for editing (not for creation)
  const openEditModal = (product) => {
    setForm({
      id: product.id, // needed for update API
      name: product.name,
      description: product.description,
      price: product.price,
      quantity: product.quantity
    });
    setShowModal(true);
  };

  return (
    <div className="container">
      <h1>🚀 Product Dashboard</h1>

      {/* Toast */}
      {toast && <div className="toast">{toast}</div>}

      {/* Add Form */}
      <div className="form">

        {/* ❌ REMOVED ID INPUT (backend generates it) */}

        <input
          placeholder="Name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />

        <input
          placeholder="Description"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />

        <input
          placeholder="Price"
          value={form.price}
          onChange={(e) => setForm({ ...form, price: e.target.value })}
        />

        <input
          placeholder="Quantity"
          value={form.quantity}
          onChange={(e) => setForm({ ...form, quantity: e.target.value })}
        />

        <button onClick={addProduct}>Add Product</button>
      </div>

      {/* Loader */}
      {loading ? (
        <div className="loader"></div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Description</th>
              <th>Price</th>
              <th>Stock</th>
              <th>Actions</th>
            </tr>
          </thead>

          <tbody>
            {products.map((p) => (
              <tr key={p.id}>
                <td>{p.id}</td>
                <td>{p.name}</td>
                <td>{p.description}</td>
                <td>₹{p.price}</td>
                <td>{p.quantity}</td>
                <td>
                  <button onClick={() => openEditModal(p)}>Edit</button>
                  <button onClick={() => deleteProduct(p.id)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Edit Modal */}
      {showModal && (
        <div className="modal">
          <div className="modal-content">
            <h2>Edit Product</h2>

            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />

            <input
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />

            <input
              value={form.price}
              onChange={(e) => setForm({ ...form, price: e.target.value })}
            />

            <input
              value={form.quantity}
              onChange={(e) => setForm({ ...form, quantity: e.target.value })}
            />

            <button onClick={updateProduct}>Update</button>
            <button onClick={() => setShowModal(false)}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;






















// import React, { useEffect, useState } from "react";
// import "./App.css";

// // Base URL for backend API
// const BASE_URL = "http://127.0.0.1:8000";

// function App() {
//   // Stores list of all products from backend
//   const [products, setProducts] = useState([]);

//   // Stores form input values (used for both add and edit)
//   const [form, setForm] = useState({
//     id: "",
//     name: "",
//     description: "",
//     price: "",
//     quantity: ""
//   });

//   // Stores ID entered in search box
//   const [searchId, setSearchId] = useState("");

//   // Tracks whether user is editing or adding
//   const [isEditing, setIsEditing] = useState(false);

//   // Runs once when component loads → fetch all products
//   useEffect(() => {
//     fetchProducts();
//   }, []);

//   // Fetch all products from backend
//   const fetchProducts = async () => {
//     try {
//       const res = await fetch(`${BASE_URL}/products`);
//       const data = await res.json();
//       setProducts(data); // store products in state
//     } catch (err) {
//       console.error("Error fetching products:", err);
//     }
//   };

//   // Handles input changes and updates form state dynamically
//   const handleChange = (e) => {
//     setForm({ ...form, [e.target.name]: e.target.value });
//   };

//   // Adds a new product (POST request)
//   const addProduct = async () => {
//     try {
//       await fetch(`${BASE_URL}/products`, {
//         method: "POST",
//         headers: {
//           "Content-Type": "application/json"
//         },
//         body: JSON.stringify({
//           ...form,
//           id: Number(form.id),           // convert to number
//           price: Number(form.price),
//           quantity: Number(form.quantity)
//         })
//       });

//       fetchProducts();   // refresh list after adding

//       setForm({ id: "", name: "", description: "", price: "", quantity: "" }); // ✅ clear form
//     } catch (err) {
//       console.error("Error adding product:", err);
//     }
//   };

//   // Updates an existing product (PUT request)
//   const updateProduct = async () => {
//     try {
//       await fetch(`${BASE_URL}/products/${form.id}`, {
//         method: "PUT",
//         headers: {
//           "Content-Type": "application/json"
//         },
//         body: JSON.stringify({
//           ...form,
//           id: Number(form.id),
//           price: Number(form.price),
//           quantity: Number(form.quantity)
//         })
//       });

//       setIsEditing(false); // exit edit mode
//       setForm({ id: "", name: "", description: "", price: "", quantity: "" }); // clear form
//       fetchProducts(); // refresh updated data
//     } catch (err) {
//       console.error("Error updating product:", err);
//     }
//   };

//   // Loads selected product into form for editing
//   const editProduct = (product) => {
//     setForm(product);      // fill form with existing data
//     setIsEditing(true);    // switch to edit mode
//   };

//   // Deletes a product (DELETE request)
//   const deleteProduct = async (id) => {
//     try {
//       await fetch(`${BASE_URL}/products/${id}`, {
//         method: "DELETE"
//       });
//       fetchProducts(); // refresh list after deletion
//     } catch (err) {
//       console.error("Error deleting product:", err);
//     }
//   };

//   // Searches product by ID
//   const searchProduct = async () => {
//   try {
//     const res = await fetch(`${BASE_URL}/products/${searchId}`);

//     if (!res.ok) {          // show only searched product
//       alert("Product not found");
//       return;
//     }

//     const data = await res.json();
//     setProducts([data]);

//   } catch (err) {
//     console.error("Error searching product:", err);
//   }
// };


//   return (
//     <div className="container">
//       <h1>🚀 Project X Dashboard</h1>

//       {/* FORM SECTION */}
//       <div className="form">
//         {/* Controlled inputs → value tied to state */}
//         <input name="id" value={form.id} placeholder="ID" onChange={handleChange} />
//         <input name="name" value={form.name} placeholder="Name" onChange={handleChange} />
//         <input name="description" value={form.description} placeholder="Description" onChange={handleChange} />
//         <input name="price" value={form.price} placeholder="Price" onChange={handleChange} />
//         <input name="quantity" value={form.quantity} placeholder="Quantity" onChange={handleChange} />

//         {/* Button switches between Add and Update */}
//         <button onClick={isEditing ? updateProduct : addProduct}>
//           {isEditing ? "Update Product" : "Add Product"}
//         </button>

//         {/* Cancel button appears only in edit mode */}
//         {isEditing && (
//           <button
//             onClick={() => {
//               setIsEditing(false); // exit edit mode
//               setForm({ id: "", name: "", description: "", price: "", quantity: "" }); // reset form
//             }}
//           >
//             Cancel
//           </button>
//         )}
//       </div>

//       {/* SEARCH SECTION */}
//       <div className="search">
//         <input
//           placeholder="Search by ID"
//           value={searchId}
//           onChange={(e) => setSearchId(e.target.value)}
//         />
//         <button onClick={searchProduct}>Search</button>
//         <button onClick={fetchProducts}>Reset</button>
//       </div>

//       {/* PRODUCT LIST */}
//       <div className="products">
//         {products.map((p) => (
//           <div key={p.id} className="card">
//             <h3>{p.name}</h3>
//             <p><strong>ID:</strong> {p.id}</p>
//             <p>{p.description}</p>
//             <p><strong>Price:</strong> ₹{p.price}</p>
//             <p><strong>Stock:</strong> {p.quantity}</p>

//             {/* Edit fills form */}
//             <button onClick={() => editProduct(p)}>Edit</button>

//             {/* Delete removes product */}
//             <button onClick={() => deleteProduct(p.id)}>Delete</button>
//           </div>
//         ))}
//       </div>
//     </div>
//   );
// }

// export default App;

// // function App() {
// //   return (
// //     <div>
// //       <h1>APP IS WORKING</h1>
// //     </div>
// //   );
// // }

// // export default App;