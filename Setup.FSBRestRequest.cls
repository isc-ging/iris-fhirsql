Class Setup.FSBRestRequest Extends %RegisteredObject
{

/// Hostname for the web gateway service on the compose network
Parameter SERVER = "localhost";

/// TCP port for Web Server
Parameter PORT = 52773;

ClassMethod ConfigureRequest(httpRequest As %Net.HttpRequest)
{
    Set httpRequest.Server = ..#SERVER
    Set httpRequest.Https = 0
    Set httpRequest.Port = ..#PORT
}

ClassMethod LocalPOSTRequest(resource As %String, filePath As %String) As %Status
{
    // Create an HTTP request object
    Set httpRequest = ##class(%Net.HttpRequest).%New()

    // Set the target URL
    Do ..ConfigureRequest(httpRequest)

    // Set the request headers (optional)
    Do httpRequest.SetHeader("Content-Type", "application/json")
    Do httpRequest.SetHeader("Accept", "application/json")
    Do httpRequest.SetHeader("Authorization", "Basic U3VwZXJVc2VyOlNZUw==")

    Set fileStream = ##class(%Stream.FileCharacter).%New()
    Do fileStream.LinkToFile(filePath)
    Do httpRequest.EntityBody.CopyFrom(fileStream)

    Set endpoint = "/csp/fhirsql/api/ui/v2/"_resource

    // Send the request
    Set status = httpRequest.Post(endpoint)

    // Check for errors
    If $$$ISERR(status) {
        Write "Error sending request: ", $SYSTEM.Status.GetErrorText(status), !
        Quit status
    }

    // Read the response
    Write "Response Code: ", httpRequest.HttpResponse.StatusCode, !
    Write "Response Data: ", httpRequest.HttpResponse.Data.Read(), !

    Quit $$$OK
}

ClassMethod WaitForAnalysisComplete(id As %String)
{   
    set timecount = 0
    for {
        quit:..GetAnalysisStatus(id)="completed"
        quit:..GetAnalysisStatus(id)="errored"
        w ..GetAnalysisStatus(id), !
        write "Waiting...", !
        set timecount = timecount + 2
        hang 2
        if timecount>120{
            write "Analysis is taking longer than expected, exiting wait loop", !
            quit
        }
    }

    write "Finished waiting", !
}

ClassMethod GetAnalysisStatus(id As %String) As %String
{
    // Create an HTTP request object
    Set httpRequest = ##class(%Net.HttpRequest).%New()

    // Set the target URL
    Do ..ConfigureRequest(httpRequest)

    // Set the request headers (optional)
    Do httpRequest.SetHeader("Content-Type", "application/json")
    Do httpRequest.SetHeader("Accept", "application/json")
    Do httpRequest.SetHeader("Authorization", "Basic U3VwZXJVc2VyOlNZUw==")

    Set endpoint = "/csp/fhirsql/api/ui/v2/analysis?ID="_id

    // Send the request
    Set status = httpRequest.Get(endpoint)

    // Check for errors
    If $$$ISERR(status) {
        Write "Error sending request: ", $SYSTEM.Status.GetErrorText(status), !
        Quit status
    }

   set responseText = httpRequest.HttpResponse.Data.Read()

    // Read the response
    Write "Response Code: ", httpRequest.HttpResponse.StatusCode, !
    #; Write "Response Data: ", responseText, !

    if httpRequest.HttpResponse.StatusCode '= 200 {
        write "Error: Received non-200 response code", !
        quit "errored"
    }

    set responseJson = {}.%FromJSON(responseText)
    set completionStatus = responseJson.status
    write "Completion Status: ", completionStatus, !

    Quit completionStatus
}

ClassMethod RunAll() As %Status
{
    Do ..LocalPOSTRequest("credentials", "/home/irisowner/dev/FHIR/SetupRequestBodies/credentials.body")
    Do ..LocalPOSTRequest("fhirrepository", "/home/irisowner/dev/FHIR/SetupRequestBodies/fhirrepository.body")
    Do ..LocalPOSTRequest("analysis", "/home/irisowner/dev/FHIR/SetupRequestBodies/analysis.body")
    Do ..WaitForAnalysisComplete(1)
    Do ..LocalPOSTRequest("transformspec", "/home/irisowner/dev/FHIR/SetupRequestBodies/transformspec.body")
    Do ..LocalPOSTRequest("projection", "/home/irisowner/dev/FHIR/SetupRequestBodies/projection.body")
}

}
