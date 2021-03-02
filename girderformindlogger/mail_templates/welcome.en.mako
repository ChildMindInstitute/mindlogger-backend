<%include file="_header.mako"/>

<div style="max-width: 440px;">

    Welcome to MindLogger! You were invited ${byCoordinator}to be ${role} of <b>${appletName}</b>${instanceName}.
    <br/>
    Below are the users that have access to your data:
    <h3>Users who can see your data for this applet: </h3>${reviewers}
    <h3>Users who can change this applet's settings, including who can access your data: </h3>${managers}
    <h3>Users who can change this applet's settings, but who cannot change who can see your data: </h3>${coordinators}
    <br/>
    ${accept}

    ## <a href="${url}/accept" style="padding: 0.28rem 0.64rem; font-size: 0.8rem; line-height: 1.5; border-radius: 0.3rem; margin: 4px; display: inline-block; font-weight: 400; text-align: center; vertical-align: middle; text-decoration: none; color: #ffffff; background-color: rgb(0, 187, 133); border-color: rgb(0, 187, 133);">Accept Invitation</a>
    ## <a href="${url}/decline" style="padding: 0.28rem 0.64rem; font-size: 0.8rem; line-height: 1.5; border-radius: 0.3rem; margin: 4px; display: inline-block; font-weight: 400; text-align: center; vertical-align: middle; text-decoration: none; color: #ffffff; background-color: rgb(255, 0, 69); border-color: rgb(255, 0, 69);">Decline Invitation</a>
</div>

<%include file="_footer.en.mako"/>
