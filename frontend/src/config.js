const required=["VITE_SUPABASE_URL","VITE_SUPABASE_PUBLISHABLE_KEY"];
export const config={apiBaseUrl:import.meta.env.VITE_API_BASE_URL||"http://127.0.0.1:8000/api/v1",supabaseUrl:import.meta.env.VITE_SUPABASE_URL,supabaseKey:import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY};
export const missingPublicConfig=required.filter(key=>!import.meta.env[key]);
