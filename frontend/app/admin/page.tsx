"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

interface User {
  _id: string;
  email: string;
  role: string;
  is_active: boolean;
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploadStatus, setUploadStatus] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const router = useRouter();

  // 🔐 helper for admin-only requests
  const adminFetch = async (url: string, method = "PATCH") => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      throw new Error("No token");
    }

    const res = await fetch(url, {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (res.status === 401 || res.status === 403) {
      router.push("/login");
      throw new Error("Unauthorized");
    }

    if (!res.ok) {
      throw new Error("Request failed");
    }
  };

  // 📤 PDF upload handler
  const handlePdfUpload = async () => {
    if (!selectedFile) {
      setUploadStatus("Please select a file first");
      return;
    }

    if (selectedFile.type !== "application/pdf") {
      setUploadStatus("Please select a PDF file");
      return;
    }

    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }

    setUploadStatus("Uploading...");

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const res = await fetch("http://localhost:8000/admin/upload-pdf", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (res.status === 401 || res.status === 403) {
        router.push("/login");
        throw new Error("Unauthorized");
      }

      if (!res.ok) {
        throw new Error("Upload failed");
      }

      const data = await res.json();
      setUploadStatus("✅ PDF uploaded successfully!");
      router.push("/")
      setSelectedFile(null);
      // Reset file input
      const fileInput = document.getElementById("pdf-input") as HTMLInputElement;
      if (fileInput) fileInput.value = "";
    } catch (err) {
      setUploadStatus("❌ Failed to upload PDF");
    }
  
  };

  // 📥 load users
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }

    fetch("http://localhost:8000/admin/user", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then(async (res) => {
        if (res.status === 401 || res.status === 403) {
          router.push("/login");
          throw new Error("Unauthorized");
        }
        if (!res.ok) {
          throw new Error("Server error");
        }
        const data = await res.json();
        if (!Array.isArray(data)) {
          throw new Error("Invalid response format");
        }
        setUsers(data);
      })
      .catch(() => {
        setError("Failed to load users");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [router]);

  if (loading) {
    return <div className="p-8 text-center">Loading users...</div>;
  }

  if (error) {
    return <div className="p-8 text-center text-red-600">{error}</div>;
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-6">Admin – Users</h1>

      {/* PDF Upload Section */}
      <div className="mb-8 p-6 bg-gray-50 rounded-lg border border-gray-200">
        <h2 className="text-xl font-semibold mb-4 text-gray-900">Upload PDF</h2>
        <div className="flex items-center gap-4 text-gray-900">
          <input
            id="pdf-input"
            type="file"
            accept=".pdf"
            onChange={(e) => {
              const file = e.target.files?.[0] || null;
              setSelectedFile(file);
              setUploadStatus("");
            }}
            className="flex-1 p-2 border border-gray-300 rounded"
          />
          <button
            onClick={handlePdfUpload}
            disabled={!selectedFile}
            className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            Upload PDF
          </button>
        </div>
        {uploadStatus && (
          <p className={`mt-2 text-sm ${uploadStatus.includes("✅") ? "text-green-600" : uploadStatus.includes("❌") ? "text-red-600" : "text-gray-600"}`}>
            {uploadStatus}
          </p>
        )}
      </div>

      {/* Users Table */}
      <table className="w-full border-collapse border border-gray-300">
        <thead>
          <tr className="bg-gray-100">
            <th className="border border-gray-300 p-2 text-gray-900">Email</th>
            <th className="border border-gray-300 p-2 text-gray-900">Role</th>
            <th className="border border-gray-300 p-2 text-gray-900">Status</th>
            <th className="border border-gray-300 p-2 text-gray-900">Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u._id}>
              <td className="border border-gray-300 p-2">{u.email}</td>
              <td className="border border-gray-300 p-2">{u.role}</td>
              <td className="border border-gray-300 p-2">
                {u.is_active ? "✅ Active" : "❌ Disabled"}
              </td>
              <td className="border border-gray-300 p-2">
                {/* Enable / Disable */}
                {u.is_active ? (
                  <button
                    onClick={async () => {
                      await adminFetch(
                        `http://localhost:8000/admin/users/${u._id}/disable`
                      );
                      setUsers((prev) =>
                        prev.map((x) =>
                          x._id === u._id ? { ...x, is_active: false } : x
                        )
                      );
                    }}
                    className="mr-2 px-3 py-1 bg-red-500 text-white rounded"
                  >
                    Disable
                  </button>
                ) : (
                  <button
                    onClick={async () => {
                      await adminFetch(
                        `http://localhost:8000/admin/users/${u._id}/enable`
                      );
                      setUsers((prev) =>
                        prev.map((x) =>
                          x._id === u._id ? { ...x, is_active: true } : x
                        )
                      );
                    }}
                    className="mr-2 px-3 py-1 bg-green-500 text-white rounded"
                  >
                    Enable
                  </button>
                )}

                {/* Role toggle */}
                {u.role === "user" ? (
                  <button
                    onClick={async () => {
                      await adminFetch(
                        `http://localhost:8000/admin/users/${u._id}/role?role=admin`
                      );
                      setUsers((prev) =>
                        prev.map((x) =>
                          x._id === u._id ? { ...x, role: "admin" } : x
                        )
                      );
                    }}
                    className="px-3 py-1 bg-blue-500 text-white rounded"
                  >
                    Make Admin
                  </button>
                ) : (
                  <button
                    onClick={async () => {
                      await adminFetch(
                        `http://localhost:8000/admin/users/${u._id}/role?role=user`
                      );
                      setUsers((prev) =>
                        prev.map((x) =>
                          x._id === u._id ? { ...x, role: "user" } : x
                        )
                      );
                    }}
                    className="px-3 py-1 bg-gray-500 text-white rounded"
                  >
                    Remove Admin
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}