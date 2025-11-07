import { Routes, Route } from "react-router-dom";
import { MainPage } from "./components/MainPage";
import { InvoicePage } from "./components/InvoicePage";
import { Toaster } from "sonner";

export default function App() {
    return (
        <div>
            <Routes>
                <Route path="/" element={<MainPage />} />
                <Route
                    path="/invoice/:invoiceNumber/:ticketNumber"
                    element={<InvoicePage />}
                />
            </Routes>
            <Toaster />
        </div>
    );
}
