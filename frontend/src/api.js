const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8001/api/extension";
async function request(path, options={}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: {"Content-Type":"application/json", ...(options.headers||{})},
    ...options
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
}
export const api = {
  environments: () => request("/environments"),
  bodySystems: () => request("/body-systems"),
  bodyStatus: (key, astronautId=1) => request(`/body-systems/${key}/status?astronaut_id=${astronautId}`),
  routines: () => request("/routines"),
  createRoutine: data => request("/routines",{method:"POST",body:JSON.stringify(data)}),
  completeRoutine: id => request(`/routines/${id}/complete`,{method:"POST",body:JSON.stringify({})}),
  challenges: () => request("/challenges"),
  completeChallenge: (id, astronautId=1) => request(`/challenges/${id}/complete/${astronautId}`,{method:"POST",body:"{}"}),
  education: () => request("/education")
};
