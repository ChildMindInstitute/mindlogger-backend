export const randomString = (length) => {
    var text = "";
    var possible = "ABCDEFGHIJKLMOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    for(var i=0; i< length; i++) {
        text +=possible.charAt(Math.floor(Math.random() * possible.length))
    }
}