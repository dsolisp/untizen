using System;
using System.Collections.Generic;
using System.IO;

static class CatalogTests
{
    static void Equal(int expected, int actual, string context)
    {
        if (expected != actual) throw new Exception(context + ": expected " + expected + ", got " + actual);
    }
    public static int Main(string[] args)
    {
        var catalog = AppLibrary.Load(args[0]);
        if (catalog.Count < 2) throw new Exception("Catalog unexpectedly small");
        Equal(-1, AppLibrary.Move(31, 0, "Up"), "top row returns to tabs");
        Equal(15, AppLibrary.Move(31, 10, "Down"), "last row enters next page");
        Equal(25, AppLibrary.Move(31, 30, "Up"), "partial page returns to matching previous column");
        Equal(30, AppLibrary.Move(31, 29, "Down"), "last partial page clamps column");
        Equal(11, AppLibrary.Move(12, 9, "Down"), "partial bottom row clamps column");
        Equal(11, AppLibrary.Move(12, 11, "Right"), "last item remains selected");
        Equal(-1, AppLibrary.Move(0, 0, "Down"), "empty catalog");
        for (int count = 1; count < 48; count++)
            for (int item = 0; item < count; item++)
                foreach (var key in new[] {"Left", "Right", "Up", "Down"})
                {
                    int next = AppLibrary.Move(count, item, key);
                    if (next < -1 || next >= count) throw new Exception("Out of bounds navigation");
                }
        string tmp = Path.GetTempFileName();
        try
        {
            foreach (string json in new[] {
                "[{\"Name\":\"Bad\",\"Id\":\"one\",\"Asset\":\"../escape.svg\",\"Width\":100,\"Height\":50}]",
                "[{\"Name\":\"Bad\",\"Id\":\"one\",\"Asset\":\"ok.svg\",\"Width\":100,\"Height\":50,\"Crop\":[0.8,0,0.4,1]}]",
                "[{\"Name\":\"A\",\"Id\":\"one\",\"Asset\":\"ok.svg\",\"Width\":100,\"Height\":50},{\"Name\":\"B\",\"Id\":\"one\",\"Asset\":\"ok.svg\",\"Width\":100,\"Height\":50}]"
            })
            {
                File.WriteAllText(tmp, json);
                bool rejected = false;
                try { AppLibrary.Load(tmp); } catch (InvalidDataException) { rejected = true; }
                if (!rejected) throw new Exception("Invalid catalog accepted");
            }
        }
        finally { File.Delete(tmp); }
        // Recents: journal recording, hero order and the dock fill.
        var journal = Recents.Record(new List<string>(), "hdmi:14");
        journal = Recents.Record(journal, "app:org.tizen.netflix-app");
        journal = Recents.Record(journal, "hdmi:14");
        if (journal[0] != "hdmi:14" || journal[1] != "app:org.tizen.netflix-app" || journal.Count != 2)
            throw new Exception("Record must move repeats to the front");
        var capped = new List<string>();
        for (int i = 0; i < Recents.JournalCap + 5; i++) capped = Recents.Record(capped, "app:id-" + i);
        Equal(Recents.JournalCap, capped.Count, "journal caps");
        if (capped[0] != "app:id-" + (Recents.JournalCap + 4)) throw new Exception("journal stays newest first");
        var ordered = Inputs.Ordered(new List<string> {"hdmi:13"}, 16);
        if (ordered[0].Source != 16 || ordered[1].Source != 13 || ordered[2].Source != 14)
            throw new Exception("live input wins, then journal, then catalogue");
        if (Inputs.Ordered(new List<string>(), 0)[0].Source != 14)
            throw new Exception("catalogue order without recents");
        var allowed = new List<string> {"app:netflix", "app:yt", "app:prime", "hdmi:14", "hdmi:13", "hdmi:16"};
        var dock = Recents.DockActions(new List<string> {"hdmi:13", "app:yt", "app:gone"}, allowed);
        Equal(5, dock.Count, "dock fills to five");
        if (dock[0] != "hdmi:13" || dock[1] != "app:yt") throw new Exception("dock follows the journal");
        if (dock[2] != "hdmi:14" || dock[3] != "app:netflix" || dock[4] != "app:prime")
            throw new Exception("dock falls back to first-run defaults without duplicates");
        string recentsTmp = Path.GetTempFileName();
        try
        {
            Recents.Save(recentsTmp, dock);
            Equal(dock.Count, Recents.Load(recentsTmp).Count, "journal roundtrip");
            File.WriteAllText(recentsTmp, "{not json");
            Equal(0, Recents.Load(recentsTmp).Count, "corrupt journal starts empty");
        }
        finally { File.Delete(recentsTmp); }
        string sourcesTmp = Path.GetTempFileName();
        try
        {
            File.WriteAllText(sourcesTmp,
                "[{\"Name\":\"Switch\",\"Source\":15,\"Tagline\":\"Docked.\",\"Description\":\"Console · HDMI\",\"Hero\":\"hero.svg\",\"Portrait\":\"portrait.svg\",\"Dock\":\"switch\"}]");
            Inputs.Load(sourcesTmp);
            Equal(1, Inputs.All.Count, "sources.json replaces the built-in list");
            if (Inputs.BySource(15)==null || Inputs.BySource(14)!=null)
                throw new Exception("loaded sources must replace the defaults");
            Inputs.Reset();
            if (Inputs.BySource(14)==null) throw new Exception("Reset restores the built-in HDMI list");
        }
        finally { File.Delete(sourcesTmp); Inputs.Reset(); }
        if (StatePaths.Prefer("/new","/old",p=>p=="/new")!="/new")
            throw new Exception("Prefer the new path when it exists");
        if (StatePaths.Prefer("/new","/old",p=>p=="/old")!="/old")
            throw new Exception("Prefer the quiet-home leftover when the new path is absent");
        if (StatePaths.Prefer("/new","/old",p=>false)!="/new")
            throw new Exception("Write the new path when neither file exists");
        // Installed catalog + two-list menu: merge, toggle, persistence.
        var curatedList = new List<LibraryApp> {
            new LibraryApp {Name="Netflix", Id="netflix", Asset="a.svg", Width=100, Height=50},
            new LibraryApp {Name="Store", Id="store", Asset="s.svg", Utility=true, Width=100, Height=50},
            new LibraryApp {Name="Gone", Id="gone", Asset="g.svg", Width=100, Height=50}};
        string installedTmp = Path.GetTempFileName();
        List<LibraryApp> installedList;
        try
        {
            File.WriteAllText(installedTmp,
                "[{\"Id\":\"netflix\"},{\"Id\":\"crunchy\",\"Name\":\"Crunchyroll\",\"Asset\":\"app-icons/installed/crunchy.png\",\"Background\":\"#f47521\"},{\"Id\":\"iptv\",\"Name\":\"IPTV Smarters\"},{\"Id\":\"bad\",\"Name\":\"Bad\",\"Asset\":\"../escape.svg\"},{\"Id\":\"netflix\"}]");
            installedList = InstalledCatalog.Load(installedTmp);
        }
        finally { File.Delete(installedTmp); }
        Equal(4, installedList.Count, "installed load dedupes and keeps valid ids");
        if (installedList.Find(a=>a.Id=="bad").Asset != InstalledCatalog.DefaultAsset)
            throw new Exception("unsafe installed artwork falls back to the neutral tile");
        if (InstalledCatalog.Load(Path.Combine(Path.GetTempPath(),"untizen-missing-catalog.json")).Count != 0)
            throw new Exception("missing installed catalog loads empty");
        var visible = MenuCatalog.Visible(curatedList, installedList, new List<string>());
        Equal(5, visible.Count, "menu keeps installed curated apps, drops uninstalled, appends the rest");
        if (visible[0].Id!="netflix"||visible[1].Id!="store"||visible[2].Id!="bad"||visible[3].Id!="crunchy"||visible[4].Id!="iptv")
            throw new Exception("menu order: curated first, then installed alphabetically");
        var noCatalog = MenuCatalog.Visible(curatedList, new List<LibraryApp>(), new List<string>{"gone"});
        Equal(2, noCatalog.Count, "without an installed catalog the curated menu still honours hidden");
        var hiddenMenu = MenuCatalog.Visible(curatedList, installedList, new List<string>{"crunchy","netflix"});
        Equal(3, hiddenMenu.Count, "hidden apps leave the menu but utility stays");
        if (hiddenMenu.Find(a=>a.Id=="store")==null) throw new Exception("utility tiles are never hidden");
        var all = MenuCatalog.All(installedList, curatedList);
        Equal(4, all.Count, "all list holds every installed app");
        if (all[0].Id!="bad"||all[1].Id!="crunchy"||all[3].Id!="netflix") throw new Exception("all list sorts by name");
        if (all[3].Asset!="a.svg") throw new Exception("all list prefers curated artwork");
        var toggled = MenuCatalog.Toggle(new List<string>{"b","a"}, "c");
        if (string.Join(",",toggled)!="a,b,c") throw new Exception("toggle adds and sorts");
        toggled = MenuCatalog.Toggle(toggled, "b");
        if (string.Join(",",toggled)!="a,c") throw new Exception("toggle removes");
        string menuTmp = Path.GetTempFileName();
        try
        {
            MenuState.Save(menuTmp, toggled);
            Equal(2, MenuState.Load(menuTmp).Count, "menu roundtrip");
            File.WriteAllText(menuTmp, "[broken");
            Equal(0, MenuState.Load(menuTmp).Count, "corrupt menu state starts empty");
        }
        finally { File.Delete(menuTmp); }
        Console.WriteLine("Catalog, navigation, invalid-input, recents and menu checks passed.");
        return 0;
    }
}
