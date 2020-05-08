<%include file="_header.mako"/>

<p>
    Hello ${userName}!
</p>
<p>
${coordinatorName} invited you to ${appletName} applet. 
</p>

<p>
    please click this link to accept invitation!
    <p><a href="${url}">${url}</a> </p>
</p>

<%include file="_footer.mako"/>
