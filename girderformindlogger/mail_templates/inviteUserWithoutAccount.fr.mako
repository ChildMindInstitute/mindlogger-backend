<%include file="_header.mako"/>

<p>
    Bonjour ${userName}!
</p>

<p>
    You were invited by ${coordinatorName} to be ${'an' if role == 'editor' else 'a'} ${role} of ${appletName} applet on MindLogger.
</p>

<p>
    Please visit <a href="${url}">here</a> to create a new account and accept invitation.
</p>

<%include file="_footer.mako"/>
