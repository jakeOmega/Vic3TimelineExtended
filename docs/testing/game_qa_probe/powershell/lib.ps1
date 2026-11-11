Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices; using System.Text; using System.Threading;
public class U {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
  [StructLayout(LayoutKind.Sequential)] public struct MOUSEINPUT { public int dx, dy; public uint mouseData, dwFlags, time; public IntPtr extra; }
  [StructLayout(LayoutKind.Sequential)] public struct KEYBDINPUT { public ushort wVk, wScan; public uint dwFlags, time; public IntPtr extra; }
  [StructLayout(LayoutKind.Explicit)] public struct IU { [FieldOffset(0)] public MOUSEINPUT mi; [FieldOffset(0)] public KEYBDINPUT ki; }
  [StructLayout(LayoutKind.Sequential)] public struct INPUT { public uint type; public IU u; }
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern uint SendInput(uint n, INPUT[] i, int size);
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
  static void Send(INPUT i) { SendInput(1, new INPUT[]{ i }, Marshal.SizeOf(typeof(INPUT))); }
  public static void Scan(ushort sc, bool up, bool ext) { INPUT i = new INPUT(); i.type = 1; i.u.ki.wScan = sc; i.u.ki.dwFlags = 0x0008u | (up ? 0x0002u : 0u) | (ext ? 0x0001u : 0u); Send(i); }
  public static void Tap(ushort sc, bool ext) { Scan(sc, false, ext); Thread.Sleep(40); Scan(sc, true, ext); Thread.Sleep(40); }
  public static void Uni(char c) { INPUT i = new INPUT(); i.type = 1; i.u.ki.wScan = c; i.u.ki.dwFlags = 0x0004; Send(i); i.u.ki.dwFlags = 0x0004 | 0x0002; Send(i); Thread.Sleep(8); }
  public static void Type(string s) { foreach (char c in s) Uni(c); }
  public static void Click(int x, int y) { SetCursorPos(x, y); Thread.Sleep(120); INPUT i = new INPUT(); i.type = 0; i.u.mi.dwFlags = 0x0002; Send(i); Thread.Sleep(60); i.u.mi.dwFlags = 0x0004; Send(i); }
  public static bool Focus(IntPtr h) { if (IsIconic(h)) ShowWindow(h, 9); keybd_event(0x12, 0, 0, UIntPtr.Zero); keybd_event(0x12, 0, 2, UIntPtr.Zero); bool ok = SetForegroundWindow(h); Thread.Sleep(300); return GetForegroundWindow() == h; }
  public static string Title(IntPtr h) { StringBuilder sb = new StringBuilder(256); GetWindowText(h, sb, 256); return sb.ToString(); }
}
"@
[U]::SetProcessDPIAware() | Out-Null
function Get-Game { Get-Process victoria3 -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1 }
function Get-ClientRect($h) { $r = New-Object U+RECT; [U]::GetClientRect($h, [ref]$r) | Out-Null; $p = New-Object U+POINT; [U]::ClientToScreen($h, [ref]$p) | Out-Null; @{ X=$p.X; Y=$p.Y; W=$r.R; H=$r.B } }
