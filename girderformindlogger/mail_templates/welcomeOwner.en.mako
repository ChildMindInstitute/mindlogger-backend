<%include file="_header.mako"/>

<div style="max-width: 440px;">

    Welcome to MindLogger! You were invited ${byCoordinator}to be ${role} of <b>${appletName}</b>${instanceName}.
    ${accept}

    <a
        href="${url}/accept"
        style="padding: 0.4rem 1rem; font-size: 0.8rem; line-height: 1.5; border-radius: 0.3rem; margin: 4px; display: inline-block; font-weight: 400; text-align: center; vertical-align: middle; text-decoration: none; color: #ffffff; background-color: rgb(88, 217, 65); border-color: rgb(88, 217, 65);"
    >
        Accept
    </a>
    <a
        href="${url}/decline"
        style="padding: 0.4rem 1rem; font-size: 0.8rem; line-height: 1.5; border-radius: 0.3rem; margin: 4px; display: inline-block; font-weight: 400; text-align: center; vertical-align: middle; text-decoration: none; color: #ffffff; background-color: rgb(224, 52, 56); border-color: rgb(224, 52, 56);"
    >
        Decline
    </a>

</div>
<%include file="_footer.mako"/>
