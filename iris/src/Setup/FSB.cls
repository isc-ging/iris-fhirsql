Class Setup.FSB Extends %RegisteredObject
{

/// Description
Parameter FHIRENDPOINT = "/readyai/r4";

ClassMethod EnableApps() As %Status
{
    New $NAMESPACE
    Set $NAMESPACE = "%SYS"
    Kill ap
    Set ap("Enabled") = 1
    Do ##class(Security.Applications).Modify("/csp/fhirsql/api/ui", .ap)
    Kill ap
    Set ap("Enabled") = 1
    Do ##class(Security.Applications).Modify("/csp/fhirsql/api/repository", .ap)
    Write "Apps enabled",!
    Quit $$$OK
}

ClassMethod InstallFoundation() As %Status
{
    New $NAMESPACE
    Set $NAMESPACE = "HSLIB"
    Set sc = ##class(HS.Util.Installer.Foundation).Install("READYAI")
    If $$$ISERR(sc) { Write "Foundation ERR: ",$System.Status.GetErrorText(sc),! }
    If $$$ISOK(sc) { Write "Foundation OK",! }
    Quit sc
}

ClassMethod InstallFHIRRepo() As %Status
{
    
    set strategyClass = "HS.FHIRServer.Storage.Json.InteractionsStrategy"
    Set metadataPackages = $lb("hl7.fhir.r4.core@4.0.1")

    // Install elements that are required for a FHIR-enabled namespace
    Do ##class(HS.FHIRServer.Installer).InstallNamespace("READYAI")

    // Install an instance of a FHIR Service into the current namespace
    Do ##class(HS.FHIRServer.Installer).InstallInstance(..#FHIRENDPOINT, strategyClass, metadataPackages)
}

ClassMethod LoadFHIRData() As %Status
{
    Do ##class(HS.FHIRServer.Tools.DataLoader).SubmitResourceFiles("/tmp/fhirdata", "FHIRServer", ..#FHIRENDPOINT, 1, "^fhirlogs")
}

ClassMethod GrantFSBRoles() As %Status
{
    New $NAMESPACE
    Set $NAMESPACE = "%SYS"
    For user = "DScully","NJoy" {
        Set sc = ##class(Security.Users).Get(user, .up)
        If sc {
            Set up("Roles") = up("Roles") _ ",FSB_Admin,FSB_Analyst,FSB_Data_Steward"
            Do ##class(Security.Users).Modify(user, .up)
            Write user, " FSB roles granted",!
        }
    }
    Quit $$$OK
}

ClassMethod RunAll() As %Status
{
    Do ..EnableApps()
    #; Do ..InstallFoundation()
    Do ..InstallFHIRRepo()
    Do ..LoadFHIRData()
    #; Do ..GrantFSBRoles()
    #; Do ##class(Setup.FSBRestRequest).RunAll()
    Quit $$$OK
}

}
